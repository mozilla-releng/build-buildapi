import mock
import socket
import os
from buildapi.lib import mq
from buildapi.model import init_buildapi_model, buildapidb
from unittest import TestCase, SkipTest
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import json
from kombu import Connection
from kombu import Exchange
from kombu import Producer
from kombu import Queue


class Tests(TestCase):

    cons = None

    def setUp(self):
        self.consumed = []
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:")
        init_buildapi_model(self.engine)

        hostname = os.environ.get('AMQP_HOSTNAME', 'localhost')
        userid = os.environ.get('AMQP_USERID', 'buildapi-test')
        password = os.environ.get('AMQP_PASSWORD', 'buildapi-test')
        self.config = {
            'carrot.hostname': hostname,
            'carrot.userid': userid,
            'carrot.vhost': '/buildapi-test',
            'carrot.password': password,
            'carrot.exchange': 'buildapi-test',
            'carrot.queue': 'buildapi-test-q1',
            'carrot.consumer.queue': 'buildapi-test-q2',
        }

    def makePair(self, messages=1):
        self.pub = mq.LoggingJobRequestPublisher(self.engine, self.config, "carrot")
        self.pub._clock = lambda: 123456

        if messages:
            amqp_conn = mq.amqp_connection_from_config(self.config, "carrot")
            try:
                self.cons = mq.JobRequestConsumer(
                    amqp_conn,
                    exchange=self.config['carrot.exchange'],
                    queue=self.config['carrot.queue'])
            except socket.error:
                raise SkipTest("cannot connect to rabbitmq at %s" % self.config['carrot.hostname'])

            # flush the queue
            while True:
                msg = self.cons.fetch()
                if not msg:
                    break
                msg.ack()
                    
            @self.cons.register_callback
            def cb(message_data, message):
                self.consumed.append(message_data)
                message.ack()

    def tearDown(self):
        # the consumers don't all have the same API..
        if self.cons:
            if hasattr(self.cons, 'disconnect'):
                self.cons.disconnect()
            else:
                self.cons.close()

    def wait(self):
        try:
            self.cons.wait(limit=1)
        except StopIteration:
            # if you use limit, wait raises StopIteration..
            pass

    def assertJobRequest(self, action, what):
        body = {u'request_id': 1, u'when': 123456}
        body.update(what)
        self.assertEqual(self.consumed, [{
            u'action': action,
            u'body': body,
            u'who': u'me'},
        ])
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
        self.makePair()
        self.assertEqual(self.pub.reprioritizeRequest(who='me', brid=10, priority=20),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('reprioritize', dict(priority=20, brid=10))

    def test_cancelRequest(self):
        self.makePair()
        self.assertEqual(self.pub.cancelRequest(who='me', brid=10),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('cancel_request', dict(brid=10))

    def test_cancelBuild(self):
        self.makePair()
        self.assertEqual(self.pub.cancelBuild(who='me', bid=10),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('cancel_build', dict(bid=10))

    def test_rebuildBuild(self):
        self.makePair()
        self.assertEqual(self.pub.rebuildBuild(who='me', bid=10, priority=20),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('rebuild_build', dict(bid=10, priority=20))

    def test_rebuildRequest(self):
        self.makePair()
        self.assertEqual(self.pub.rebuildRequest(who='me', brid=10, priority=20),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('rebuild_request', dict(brid=10, priority=20))

    def test_cancelRevision(self):
        self.makePair()
        self.assertEqual(self.pub.cancelRevision(who='me', branch='branch1', revision='abcd'),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('cancel_revision', dict(branch=u'branch1', revision='abcd'))

    def test_newBuildAtRevision(self):
        self.makePair()
        self.assertEqual(self.pub.newBuildAtRevision(who='me', branch='branch1', revision='abcd'),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('new_build_at_revision', dict(branch=u'branch1', revision='abcd'))

    def test_newPGOBuildAtRevision(self):
        self.makePair()
        self.assertEqual(self.pub.newPGOBuildAtRevision(who='me', branch='branch1', revision='abcd', priority=2),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('new_pgobuild_at_revision', dict(branch=u'branch1', revision='abcd', priority=2))

    def test_newNightlyAtRevision(self):
        self.makePair()
        self.assertEqual(self.pub.newNightlyAtRevision(who='me', branch='branch1', revision='abcd', priority=2),
                dict(status='OK', request_id=1))
        self.wait()
        self.assertJobRequest('new_nightly_at_revision', dict(branch=u'branch1', revision='abcd', priority=2))

    def test_send_msg_db_error(self):
        self.makePair(0)
        with mock.patch.object(self.pub, 'session') as sess:
            sess.side_effect = RuntimeError
            self.assertEqual(self.pub.cancelRequest(who='me', brid=10),
                {'msg': "Couldn't create JobRequest row", 'status': 'FAILED'})

    def test_send_msg_send_error(self):
        self.makePair(0)
        with mock.patch.object(mq.JobRequestPublisher, 'send_msg') as sess:
            sess.side_effect = RuntimeError
            self.assertEqual(self.pub.cancelRequest(who='me', brid=10),
                {'msg': "Couldn't send message to broker", 'status': 'FAILED'})
            
    def test_done_acks(self):
        self.pub = mq.JobRequestDonePublisher(self.config, "carrot")
        self.cons = mq.LoggingJobRequestDoneConsumer(self.engine, self.config, "carrot")
        self.cons._clock = lambda: 123456

        # add a fake job request
        r = buildapidb.JobRequest(action='act', who='me', when=123456, what='json')
        s = sessionmaker(bind=self.engine)()
        s.add(r)
        s.commit()

        # ack it
        msg = {'body': 'action result', 'request_id': r.id}
        try:
            self.pub.ack_msg(msg)
        except socket.error:
            raise SkipTest("cannot connect to rabbitmq at %s" % self.config['carrot.hostname'])

        # receive the ack
        try:
            self.cons.wait(limit=1)
        except StopIteration:
            # if you use limit, wait raises StopIteration..
            pass

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
