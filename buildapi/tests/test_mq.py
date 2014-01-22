import mock
import socket
import os
from buildapi.lib import mq
from buildapi.model import init_buildapi_model, buildapidb
from unittest import TestCase, SkipTest
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import json
from kombu.pools import connections
from kombu import Connection
from kombu import Exchange
from kombu import Producer
from kombu import Queue


class Base(object):

    cons = None

    def setUp(self):
        self.consumed = []
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:")
        init_buildapi_model(self.engine)

        hostname = os.environ.get('AMQP_HOSTNAME', 'localhost')
        userid = os.environ.get('AMQP_USERID', 'buildapi-test')
        password = os.environ.get('AMQP_PASSWORD', 'buildapi-test')
        self.config = {
            'mq.heartbeat_interval': '5',
            'mq.kombu_url': 'amqp://%s:%s@%s//buildapi-test' % (userid, password, hostname),
            'mq.exchange': 'buildapi-test',
            'mq.queue.web': 'buildapi-test-q1',
            'mq.queue.agent': 'buildapi-test-q2',
        }

        # this is the first place we try to connect, so if we get a socket
        # error here, then the rabbitmq server isn't present, so skip the test.
        try:
            self._cleanup()
        except socket.error:
            raise SkipTest("could not reach rabbitmq server on %s" % hostname)

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        self.delete_queue('buildapi-test-q1')
        self.delete_queue('buildapi-test-q2')
        self.delete_exchange('buildapi-test')

    def _connect(self):
        return connections[Connection(self.config['mq.kombu_url'])].acquire(block=True)

    def delete_queue(self, queue_name):
        with self._connect() as conn:
            queue = Queue(queue_name)
            try:
                queue(conn).declare()
            except Exception:
                # probably no such queue
                return
            queue(conn).delete()

    def delete_exchange(self, exch_name):
        with self._connect() as conn:
            exch = Exchange(exch_name)
            try:
                exch(conn).declare()
            except Exception:
                # probably no such exchange
                return
            exch(conn).delete()

    def get_message(self, queue_name):
        with self._connect() as conn:
            queue = Queue(queue_name)
            msg = queue(conn).get()
            if msg:
                msg.ack()
            return msg

    def declare(self, thing):
        with self._connect() as conn:
            thing(conn).declare()

    def send_message(self, exchange_name, routing_key, message):
        with self._connect() as conn:
            pub = Producer(conn)
            pub.publish(message,
                         exchange=Exchange(exchange_name),
                         routing_key=routing_key)

    def patch_consumer_to_stop(self, cons):
        # monkey-patch receive to also stop the consumer after the message is received
        old_receive = cons.receive
        def receive(message_data, message):
            old_receive(message_data, message)
            cons.should_stop = True
        cons.receive = receive


class TestReliableConsumer(Base, TestCase):

    def test_consume_one(self):
        testcase = self

        class MyReliableConsumer(mq.ReliableConsumer):
            routing_key = 'requests'
            queue_name_config = 'mq.queue.web'

            def receive(self, body, message):
                self.got_body = body
                self.should_stop = True
                message.ack()

            def on_iteration(self):
                testcase.send_message('buildapi-test',
                                      'requests',
                                      {"request": "body"})
                super(MyReliableConsumer, self).on_iteration()

        cons = MyReliableConsumer(self.config)
        cons.run()
        self.assertEqual(cons.got_body, {"request": "body"})

    def test_consume_until_idle(self):
        class MyReliableConsumer(mq.ReliableConsumer):
            routing_key = 'requests'
            queue_name_config = 'mq.queue.web'
            got_messages = 0

            def receive(self, body, message):
                self.got_messages += 1
                message.ack()

        cons = MyReliableConsumer(self.config)
        self.declare(cons.queue)
        self.send_message('buildapi-test', 'requests', 'one')
        self.send_message('buildapi-test', 'requests', 'two')
        self.send_message('buildapi-test', 'requests', 'three')
        cons.run_until_idle()
        self.assertEqual(cons.got_messages, 3)


class TestReliablePublisher(Base, TestCase):

    def test_consume_one(self):

        class MyReliablePublisher(mq.ReliablePublisher):
            routing_key = 'test-message'

        pub = MyReliablePublisher(self.config)

        exchange = Exchange('buildapi-test', type='topic')
        self.declare(exchange)
        queue = Queue('buildapi-test-q1', exchange=exchange, routing_key='test-message')
        self.declare(queue)

        pub.send(message_data={'message': 'body'})
        msg = self.get_message('buildapi-test-q1')
        self.assertEqual(msg.payload, {'message': 'body'})


class TestRequester(Base, TestCase):

    def make_publisher(self, messages=1):
        self.pub = mq.LoggingJobRequestPublisher(self.engine, self.config)
        self.pub._clock = lambda: 123456

        # set up the queue to listen for it
        exchange = Exchange('buildapi-test', type='topic')
        self.declare(Queue('buildapi-test-q1',
                           exchange=exchange,
                           routing_key='requests'))

    def assertJobRequest(self, action, what):
        body = {u'request_id': 1, u'when': 123456}
        body.update(what)

        self.assertEqual(self.get_message('buildapi-test-q1').payload, {
            u'action': action,
            u'body': body,
            u'who': u'me'},
        )
        reqs = [dict(r) for r in
                self.engine.execute('select * from jobrequests')]
        for req in reqs:
            req['what'] = json.loads(req['what'])
        self.assertEqual(reqs, [{
            u'id': 1,
            u'action': action,
            u'what': what,
            u'complete_data': None,
            u'completed_at': None,
            u'when': 123456,
            u'who': u'me',
        }])

    def test_reprioritizeRequest(self):
        self.make_publisher()
        self.assertEqual(self.pub.reprioritizeRequest(who='me', brid=10, priority=20),
                dict(status='OK', request_id=1))
        self.assertJobRequest('reprioritize', dict(priority=20, brid=10))

    def test_cancelRequest(self):
        self.make_publisher()
        self.assertEqual(self.pub.cancelRequest(who='me', brid=10),
                dict(status='OK', request_id=1))
        self.assertJobRequest('cancel_request', dict(brid=10))

    def test_cancelBuild(self):
        self.make_publisher()
        self.assertEqual(self.pub.cancelBuild(who='me', bid=10),
                dict(status='OK', request_id=1))
        self.assertJobRequest('cancel_build', dict(bid=10))

    def test_rebuildBuild(self):
        self.make_publisher()
        self.assertEqual(self.pub.rebuildBuild(who='me', bid=10, priority=20),
                dict(status='OK', request_id=1))
        self.assertJobRequest('rebuild_build', dict(bid=10, priority=20))

    def test_rebuildRequest(self):
        self.make_publisher()
        self.assertEqual(self.pub.rebuildRequest(who='me', brid=10, priority=20),
                dict(status='OK', request_id=1))
        self.assertJobRequest('rebuild_request', dict(brid=10, priority=20))

    def test_cancelRevision(self):
        self.make_publisher()
        self.assertEqual(self.pub.cancelRevision(who='me', branch='branch1', revision='abcd'),
                dict(status='OK', request_id=1))
        self.assertJobRequest('cancel_revision', dict(branch=u'branch1', revision='abcd'))

    def test_newBuildAtRevision(self):
        self.make_publisher()
        self.assertEqual(self.pub.newBuildAtRevision(who='me', branch='branch1', revision='abcd'),
                dict(status='OK', request_id=1))
        self.assertJobRequest('new_build_at_revision', dict(branch=u'branch1', revision='abcd'))

    def test_newPGOBuildAtRevision(self):
        self.make_publisher()
        self.assertEqual(self.pub.newPGOBuildAtRevision(who='me', branch='branch1', revision='abcd', priority=2),
                dict(status='OK', request_id=1))
        self.assertJobRequest('new_pgobuild_at_revision', dict(branch=u'branch1', revision='abcd', priority=2))

    def test_newNightlyAtRevision(self):
        self.make_publisher()
        self.assertEqual(self.pub.newNightlyAtRevision(who='me', branch='branch1', revision='abcd', priority=2),
                dict(status='OK', request_id=1))
        self.assertJobRequest('new_nightly_at_revision', dict(branch=u'branch1', revision='abcd', priority=2))

    def test_send_msg_db_error(self):
        self.make_publisher(0)
        with mock.patch.object(self.pub, 'session') as sess:
            sess.side_effect = RuntimeError
            self.assertEqual(self.pub.cancelRequest(who='me', brid=10),
                {'msg': "Couldn't create JobRequest row", 'status': 'FAILED'})

    def test_send_msg_send_error(self):
        self.make_publisher(0)
        with mock.patch.object(mq.JobRequestPublisher, 'send_msg') as sess:
            sess.side_effect = RuntimeError
            self.assertEqual(self.pub.cancelRequest(who='me', brid=10),
                {'msg': "Couldn't send message to broker", 'status': 'FAILED'})
            
    def test_done_acks(self):
        cons = mq.LoggingJobRequestDoneConsumer(self.engine, self.config)
        cons._clock = lambda: 123456
        self.patch_consumer_to_stop(cons)

        # cheat and declare the queue so that it receives our produced message
        self.declare(cons.queue)

        # add a fake job request
        r = buildapidb.JobRequest(action='act', who='me', when=123456, what='json')
        s = sessionmaker(bind=self.engine)()
        s.add(r)
        s.commit()

        # ack it
        msg = {'body': 'action result', 'request_id': r.id}
        self.send_message('buildapi-test', 'finished', msg)

        # receive the ack
        cons.run()

        # verify that it was acked
        reqs = [dict(r) for r in
                self.engine.execute('select * from jobrequests')]
        self.assertEqual(reqs, [{
            u'what': u'json',
            u'who': u'me',
            u'when': 123456,
            u'complete_data': u'{"body": "action result", "request_id": 1}',
            u'completed_at': 123456,
            u'action': u'act',
            u'id': 1},
        ])


class TestWorker(Base, TestCase):

    def make_consumer(self):
        cons = mq.JobRequestConsumer(self.config)
        self.patch_consumer_to_stop(cons)
        return cons
    
    def make_publisher(self):
        pub = mq.JobRequestDonePublisher(self.config)
        # set up the queue to listen for it
        exchange = Exchange('buildapi-test', type='topic')
        self.declare(Queue('buildapi-test-q1',
                           exchange=exchange,
                           routing_key='finished'))
        return pub

    def test_consumer_callback(self):
        cons = self.make_consumer()

        def cb(message_data, message):
            self.consumed = message_data
        cons.register_callback(cb)

        # cheat and declare the queue so that it receives our produced message
        self.declare(cons.queue)
        # send a message
        self.send_message('buildapi-test', 'requests', {'hello': 'world'})
        # receive it
        cons.run()
        # and see that the callback ran
        self.assertEqual(self.consumed, {'hello': 'world'})

    def test_producer_ack_msg(self):
        pub = self.make_publisher()
        msg = {'body': {'hello': 'world'}, 'request_id': 1}
        pub.ack_msg(msg)
        got_msg = self.get_message('buildapi-test-q1')
        self.assertEqual(got_msg.payload, msg)

class TestRoundTrip(Base, TestCase):

    def test_round_trip(self):
        req_pub = mq.LoggingJobRequestPublisher(self.engine, self.config)
        req_pub._clock = lambda: 123456

        req_cons = mq.JobRequestConsumer(self.config)
        self.patch_consumer_to_stop(req_cons)
        self.declare(req_cons.queue)

        done_pub = mq.JobRequestDonePublisher(self.config)

        done_cons = mq.LoggingJobRequestDoneConsumer(self.engine, self.config)
        done_cons._clock = lambda: 123999
        self.patch_consumer_to_stop(done_cons)
        self.declare(done_cons.queue)

        # build a fake agent
        @req_cons.register_callback
        def agent_receive_message(message_data, message):
            msg = {'body': 'result of %s' % (message_data['action'])}
            msg['request_id'] = message_data['body']['request_id']
            done_pub.ack_msg(msg)

        # run it!
        req_pub.cancelRequest('me', 1234)
        req_cons.run()
        done_cons.run()
        reqs = [dict(r) for r in
                self.engine.execute('select * from jobrequests')]
        self.assertEqual(reqs, [{
            u'action': u'cancel_request',
            u'what': u'{"brid": 1234}',
            u'who': u'me',
            u'when': 123456,
            u'complete_data': u'{"body": "result of cancel_request", "request_id": 1}',
            u'completed_at': 123999,
            u'id': 1},
        ])
