"""
Message Queue module for buildapi.  Implements helper classes to cope with the
connection to the message broker going away, and specific publishers/consumers
to work with buildapi's expected messages.
"""
import time

from sqlalchemy.orm import sessionmaker

from kombu import Connection
from kombu import Exchange
from kombu import Queue
from kombu.mixins import ConsumerMixin
from kombu.pools import connections
from kombu.pools import producers

from buildapi.lib import json
import buildapi.model.buildapidb as buildapidb

import logging
log = logging.getLogger(__name__)

class ConfigMixin(object):

    def setup_config(self, config):
        self.heartbeat = int(config.get('mq.heartbeat_interval', '0'))
        conn = Connection(config['mq.kombu_url'], heartbeat=self.heartbeat)
        self.connection = connections[conn].acquire(block=True)
        self.exchange = Exchange(config['mq.exchange'], type='topic', durable=True)

    def get_queue(self, queue_name, routing_key):
        return Queue(queue_name,
                     durable=True,
                     routing_key=routing_key,
                     exchange=self.exchange)


class ReliableConsumer(ConfigMixin, ConsumerMixin):
    """Reliably consume messages from a given queue, based on config.  This will
    reconnect repeatedly on connection failures.

    Subclasses should specify the routing key as a class attribute.  The queue
    name comes from the configuration, based on a key specified at the class
    level, `queue_name_config`

    Override the `receive` method to handle incoming messages, remembering
    to call the message's `ack` method.

    Call the `run` method to run forever, or until `should_stop` is set.
    Alternately, call ``run_until_idle``, which will run until there is an
    iteration with no messages.
    """

    routing_key = None
    queue_name_config = None

    def __init__(self, config):
        self.setup_config(config)
        self.queue = self.get_queue(config[self.queue_name_config], self.routing_key)
        self.stop_on_idle = False
        self.messages_received = 1

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue, callbacks=[self.receive])]

    def on_connection_error(self, exc, interval):
        log.warning("Kombu connection failed (%s); waiting %ds" % (exc, interval))

    def on_connection_revived(self):
        log.warning("Kombu connection revived")

    def on_consume_ready(self, conn, channel, consumers):
        # capture the active connection, which is a clone of self.connection,
        # so that we can call heartbeat_check on the proper connection.
        self.active_connection = conn

    def on_iteration(self):
        # check the heartbeat, promising that we'll call a little over once per
        # second, which appears to be the frequency at which this method is called
        self.active_connection.heartbeat_check(self.heartbeat + 1)

    def receive(self, body, message):
        # don't forget to message.ack()
        raise NotImplementedError

    def run_until_idle(self):
        # just fetch messages until we're done
        bound_queue = self.queue(self.connection)
        while True:
            msg = bound_queue.get()
            if not msg:
                return
            self.receive(msg.payload, msg)


class ReliablePublisher(ConfigMixin):
    """Reliably produce messages with the givent routing key.
    This will automatically retry if there are connection failures.

    Subclasses should specify the routing key as a class attribute.

    Call the `send_msg` method to send a message.
    """

    routing_key = None

    def __init__(self, config):
        self.setup_config(config)

    def retry_errback(self, exc, interval):
        log.warning("Kombu connection failed (%s); waiting %ds" % (exc, interval))

    def send(self, message_data):
        with producers[self.connection].acquire(block=True) as prod:
            prod.publish(message_data,
                    exchange=self.exchange,
                    routing_key=self.routing_key,
                    declare=[self.exchange],
                    retry=True,
                    retry_policy={
                        'errback': self.retry_errback,
                        'interval_max': 2})


class JobRequestDoneConsumer(ReliableConsumer):
    """For webapp to get notified that jobs have been completed."""
    routing_key = 'finished'
    queue_name_config = 'mq.queue.web'


class JobRequestPublisher(ReliablePublisher):
    """For publishing job requests"""
    routing_key = 'requests'

    def send_msg(self, action, who, **kwargs):
        msg = {'action': action,
               'who': who,
               'body': kwargs.copy(),
               }
        log.info("Sending %s", msg)
        self.send(message_data=msg)

    def reprioritizeRequest(self, who, brid, priority):
        return self.send_msg('reprioritize', who=who, brid=brid, priority=priority)

    def cancelRequest(self, who, brid):
        return self.send_msg('cancel_request', who=who, brid=brid)

    def cancelBuild(self, who, bid):
        return self.send_msg('cancel_build', who=who, bid=bid)

    def rebuildBuild(self, who, bid, priority):
        return self.send_msg('rebuild_build', who=who, bid=bid, priority=priority)

    def rebuildRequest(self, who, brid, priority):
        return self.send_msg('rebuild_request', who=who, brid=brid, priority=priority)

    def cancelRevision(self, who, branch, revision):
        return self.send_msg('cancel_revision', who=who, branch=branch, revision=revision)

    def newBuildAtRevision(self, who, branch, revision):
        return self.send_msg('new_build_at_revision', who=who, branch=branch, revision=revision)

    def newPGOBuildAtRevision(self, who, branch, revision, priority):
        return self.send_msg('new_pgobuild_at_revision', who=who, branch=branch, revision=revision, priority=priority)

    def newNightlyAtRevision(self, who, branch, revision, priority):
        return self.send_msg('new_nightly_at_revision', who=who, branch=branch, revision=revision, priority=priority)


class JobRequestConsumer(ReliableConsumer):
    """For agents consuming job requests."""
    routing_key = 'requests'
    queue_name_config = 'mq.queue.agent'

    callback = None

    def register_callback(self, cb):
        self.callback = cb

    def receive(self, message_data, message):
        if self.callback:
            self.callback(message_data, message)


class JobRequestDonePublisher(ReliablePublisher):
    """For agents publishing job completion messages."""
    routing_key = 'finished'

    def ack_msg(self, message_data):
        self.send(message_data)


class LoggingJobRequestDoneConsumer(JobRequestDoneConsumer):
    """For webapp to get notified that jobs have been completed, and update job
    status in DB."""

    # For testing, so we can override what time it is
    _clock = time.time

    def __init__(self, engine, *args, **kwargs):
        JobRequestDoneConsumer.__init__(self, *args, **kwargs)
        self.engine = engine
        self.session = sessionmaker(bind=engine)

    def receive(self, message_data, message):
        """Handles new job completion messages.  Marks them as finished in the
        DB by setting the complete_at and complete_data columsn."""
        try:
            log.info("Got %s", message_data)
            now = self._clock()
            s = self.session()
            r = s.query(buildapidb.JobRequest).get(message_data['request_id'])
            if not r:
                log.warn("Couldn't find message %s", message_data['request_id'])
            else:
                log.info("Updating complete data")
                r.completed_at = now
                r.complete_data = json.dumps(message_data)
                s.commit()
            message.ack()
        except:
            log.exception("Unable to process message %s", message_data)


class LoggingJobRequestPublisher(JobRequestPublisher):
    """For publishing job requests, recording them first in the database."""

    # For testing, so we can override what time it is
    _clock = time.time

    def __init__(self, engine, *args, **kwargs):
        JobRequestPublisher.__init__(self, *args, **kwargs)
        self.engine = engine
        self.session = sessionmaker(bind=engine)

    def send_msg(self, action, who, **kwargs):
        """Wrap JobRequestPublisher.send_msg by first logging the request in
        the DB, and then sending the message to the broker."""
        try:
            what = json.dumps(kwargs)
            when = self._clock()
            r = buildapidb.JobRequest(action=action, who=who, when=when, what=what)
            s = self.session()
            s.add(r)
            s.commit()
        except:
            log.exception("Couldn't create JobRequest row")
            return {"status": "FAILED", "msg": "Couldn't create JobRequest row"}

        try:
            JobRequestPublisher.send_msg(self, action, who, when=r.when,
                    request_id=r.id, **kwargs)
        except:
            log.exception("Couldn't send message")
            # TODO: What do we do with r?  Mark it as done/failed, or try and
            # pick it up again later?  Return job id anyway?
            return {"status": "FAILED", "msg": "Couldn't send message to broker"}
        return {"status": "OK", "request_id": r.id}


