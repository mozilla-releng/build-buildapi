"""
Message Queue module for buildapi.  Implements helper classes to cope with the
connection to the message broker going away, and specific publishers/consumers
to work with buildapi's expected messages.
"""
import time

from sqlalchemy.orm import sessionmaker

from carrot.messaging import Publisher, Consumer
from carrot.connection import AMQPConnection
import socket

from buildapi.lib import json
import buildapi.model.buildapidb as buildapidb

import logging
log = logging.getLogger(__name__)

def amqp_connection_from_config(config, keyroot):
    """Return an AMQP connection according to the values specifed in config under keyroot.

    Will look up parameters hostname, userid, password, port (default 5672),
    ssl (default False), and vhost (default /) by key lookups in config, e.g.:

        hostname = config['%s.hostname' % keyroot]
    """
    hostname = config["%s.hostname" % keyroot]
    userid = config["%s.userid" % keyroot]
    password = config["%s.password" % keyroot]
    port = int(config.get("%s.port" % keyroot, 5672))
    ssl = bool(config.get("%s.ssl" % keyroot, False))
    vhost = config.get("%s.vhost" % keyroot, "/")

    conn = AMQPConnection(hostname=hostname, userid=userid, password=password,
            port=port, ssl=ssl, virtual_host=vhost)

    return conn

class ReconnectingPublisher(object):
    """Wrapper class around carrot.messaging.Publisher that checks its
    connection to the Broker for each message being sent.

    You can pretend this is a publisher insofar as calling send() is the same.
    """
    exchange_type = 'topic'
    routing_key = None

    def __init__(self, config, keyroot):
        self.config = config
        self.keyroot = keyroot

        self.exchange = config["%s.exchange" % keyroot]

        self.connection = None

    def connect(self):
        if not self.connection:
            self.connection = amqp_connection_from_config(self.config, self.keyroot)

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def send(self, *args, **kwargs):
        self.connect()

        publisher = Publisher(connection=self.connection,
                              exchange=self.exchange,
                              exchange_type=self.exchange_type,
                              routing_key=self.routing_key)

        retval = publisher.send(*args, **kwargs)
        publisher.close()
        return retval

class ReconnectingConsumer(object):
    """Wrapper class around carrot.messaging.Consumer that handles disconnects
    from the broker in the wait() loop."""
    def __init__(self, config, keyroot):
        self.config = config
        self.keyroot = keyroot

        self.exchange = config["%s.exchange" % keyroot]
        self.queue = config["%s.consumer.queue" % keyroot]

        self.connection = None

    def connect(self):
        if not self.connection:
            self.connection = amqp_connection_from_config(self.config, self.keyroot)

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def wait(self, limit=None):
        sleep_time = 1
        while True:
            try:
                self.connect()
                consumer = Consumer(connection=self.connection,
                                    exchange=self.exchange,
                                    exchange_type=self.exchange_type,
                                    routing_key=self.routing_key,
                                    queue=self.queue)
                # Looks like we were able to connect ok, so reset our sleep
                # time to 1
                sleep_time = 1
                consumer.register_callback(self.receive)
                consumer.wait(limit)
            except self.connection.ConnectionException:
                log.info("Lost connection, trying again in %is", sleep_time)
                self.disconnect()
                time.sleep(sleep_time)
                sleep_time = min(sleep_time*2, 60)
            except socket.error:
                log.info("Connection refused, trying again in %is", sleep_time)
                self.disconnect()
                time.sleep(sleep_time)
                sleep_time = min(sleep_time*2, 60)

class JobRequestPublisher(ReconnectingPublisher):
    """For publishing job requests"""
    routing_key = 'requests'
    exchange_type = 'topic'

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

class JobRequestConsumer(Consumer):
    """For agents consuming job requests."""
    routing_key = 'requests'
    exchange_type = 'topic'

class JobRequestDonePublisher(ReconnectingPublisher):
    """For agents publishing job completion messages."""
    routing_key = 'finished'
    exchange_type = 'topic'

    def ack_msg(self, message_data):
        self.send(message_data, routing_key=self.routing_key)

class JobRequestDoneConsumer(ReconnectingConsumer):
    """For webapp to get notified that jobs have been completed."""
    routing_key = 'finished'
    exchange_type = 'topic'

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
            now = self._clock()
            s = self.session()
            r = s.query(buildapidb.JobRequest).get(message_data['request_id'])
            if not r:
                log.warn("Couldn't find message %s", message_data['request_id'])
            else:
                r.completed_at = now
                r.complete_data = json.dumps(message_data)
                s.commit()
            message.ack()
        except:
            log.exception("Unable to process message %s", message_data)
