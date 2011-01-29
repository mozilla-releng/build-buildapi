#!/usr/bin/python
"""selfserve-agent.py [options]

Gets any messages and executes them."""
import logging as log
import time
import urllib
import subprocess
from collections import namedtuple

from sqlalchemy import text

from buildapi.lib import json

BranchInfo = namedtuple('BranchInfo', ['revlink', 'repo_path'])

class BuildAPIAgent:
    def __init__(self, db, masters_url, buildbot, sendchange_master, publisher, branch_map):
        self.db = db
        self.masters_url = masters_url
        self.buildbot = buildbot
        self.sendchange_master = sendchange_master
        self.publisher = publisher
        self.branch_map = branch_map

        self._last_masters_update = 0

    def _refresh_masters(self):
        # Refresh every 5 minutes
        if time.time() - self._last_masters_update > 300:
            log.info("Loading masters from %s", self.masters_url)
            self.masters = json.load(urllib.urlopen(self.masters_url))
            self._last_masters_update = time.time()

    def _get_repo_path(self, branch):
        return self.branch_map[branch].repo_path

    def _get_revlink(self, branch, revision):
        repo_path = self.branch_map[branch].repo_path
        return self.branch_map[branch].revlink % dict(repo_path=repo_path, branch=branch, revision=revision)

    def _get_master_pb(self, name):
        for master in self.masters:
            if master['name'] == name:
                return "%s:%i" % (master['hostname'], master['pb_port'])
        raise KeyError("master '%s' not found" % name)

    def _get_master_url(self, claimed_by_name):
        for master in self.masters:
            if master['db_name'] == claimed_by_name:
                return "http://%(hostname)s:%(http_port)i" % master
        raise KeyError("master '%s' not found" % claimed_by_name)

    def _get_build_url(self, claimed_by_name, builder_name, build_number):
        master_url = self._get_master_url(claimed_by_name)
        return "%s/builders/%s/builds/%s" % (master_url, urllib.quote(builder_name, ""), build_number)

    def _get_cancel_url(self, claimed_by_name, builder_name, build_number):
        build_url = self._get_build_url(claimed_by_name, builder_name, build_number)
        return "%s/stop" % build_url

    def _cancel_build(self, claimed_by_name, builder_name, build_number, who, comments):
        cancel_url = self._get_cancel_url(claimed_by_name, builder_name, build_number)
        data = urllib.urlencode({
            "comments": comments,
            "username": who,
            })
        urllib.urlopen(cancel_url, data)

    def receive_message(self, message_data, message):
        log.debug("Received %s", message_data)
        if 'action' not in message_data:
            # Leave it alone
            log.warn("No action found in %s", message_data)
            return
        action = message_data['action']

        action_func = getattr(self, "do_%s" % action, None)
        if not action_func:
            # We don't know how to handle this, leave it alone
            log.info("Don't know how to handle action %s" % action)
            return

        self._refresh_masters()

        try:
            retval = action_func(message_data, message)
            msg = {'body': retval}
            msg['request_id'] = message_data['body']['request_id']
            self.publisher.ack_msg(msg)
            message.ack()
        except:
            log.exception("Error processing message")

    def do_reprioritize(self, message_data, message):
        who = message_data['who']
        brid = message_data['body']['brid']
        priority = message_data['body']['priority']
        log.info("reprioritizing request by %s of request %s to priority %s",
                who, brid, priority)

        # Check that the request is still active
        request = self.db.execute(text("SELECT * FROM buildrequests WHERE id=:brid"), brid=brid).fetchone()
        if not request:
            log.info("No request with id %s, giving up" % brid)
            return {"errors": True, "msg": "No request with that id"}

        if request.complete_at and request.complete:
            log.info("request is complete, nothing to do")
            return {"errors": False, "msg": "Request is complete, nothing to do"}

        result = self.db.execute(text("UPDATE buildrequests SET priority=:priority WHERE id=:brid"),
                priority=priority,
                brid=brid,
                )
        log.debug("updated DB: %i", result.rowcount)
        if result.rowcount != 1:
            return {"errors": True, "msg": "%i rows affected" % result.rowcount}
        return {"errors": False, "msg": "Ok"}

    def do_cancel_request(self, message_data, message):
        who = message_data['who']
        brid = message_data['body']['brid']
        log.info("cancelling request by %s of %s", who, brid)

        # Check that the request is still active
        request = self.db.execute(text("SELECT * FROM buildrequests WHERE id=:brid"), brid=brid).fetchone()

        if not request:
            log.info("No request with id %s, giving up" % brid)
            return {"errors": True, "msg": "No request with that id"}

        if request.complete_at and request.complete:
            log.info("request is complete, nothing to do")
            return {"errors": False, "msg": "Request is complete, nothing to do"}

        if request.claimed_at:
            log.info("request is running, going to cancel it!")
            build = self.db.execute(text("SELECT * from builds where brid=:brid and finish_time is null"), brid=brid).fetchone()
            cancel_url = self._get_cancel_url(request.claimed_by_name, request.buildername, build.number)
            log.debug("Cancelling at %s", cancel_url)
            try:
                self._cancel_build(request.claimed_by_name, request.buildername, build.number, who, "Cancelled via self-serve")
                return {"errors": False, "msg": "Ok"}
            except:
                log.exception("Couldn't cancel build")
                return {"errors": True, "msg": "Error cancelling build"}

        log.info("request is pending, going to cancel it")
        now = time.time()
        result = self.db.execute(text("UPDATE buildrequests SET complete=1, results=2, complete_at=:now WHERE id=:brid"),
                brid=brid,
                now=now,
                )
        log.debug("updated DB: %i", result.rowcount)
        if result.rowcount != 1:
            return {"errors": True, "msg": "%i rows affected" % result.rowcount}
        return {"errors": False, "msg": "Ok"}

    def do_rebuild_build(self, message_data, message):
        who = message_data['who']
        bid = message_data['body']['bid']
        log.info("rebuilding build by %s of %s", who, bid)

        # Get the build request and build set
        build = self.db.execute(text("""\
                SELECT * FROM
                    buildrequests, buildsets, builds WHERE
                    builds.id=:bid AND
                    builds.brid = buildrequests.id AND
                    buildrequests.buildsetid = buildsets.id"""),
            bid=bid).fetchone()

        if not build:
            log.info("No build with id %s, giving up" % bid)
            return {"errors": True, "msg": "No build with that id"}

        # Create a new buildset
        q = text("""INSERT INTO buildsets
            (`external_idstring`, `reason`, `sourcestampid`, `submitted_at`, `complete`, `complete_at`, `results`)
            VALUES
            (:idstring, :reason, :sourcestampid, :submitted_at, 0, NULL, NULL)""")
        log.debug(q)

        now = time.time()
        r = self.db.execute(q,
                idstring=build.external_idstring,
                reason='Rebuilt by %s' % who,
                sourcestampid=build.sourcestampid,
                submitted_at=now,
                )

        buildsetid = r.lastrowid
        log.debug("Created buildset %s", buildsetid)

        # Copy buildset properties
        q = text("""INSERT INTO buildset_properties
                (`buildsetid`, `property_name`, `property_value`)
                SELECT :buildsetid, `property_name`, `property_value` FROM
                    buildset_properties WHERE
                    buildsetid = :oldbsid""")
        log.debug(q)
        r = self.db.execute(q,
                buildsetid=buildsetid,
                oldbsid=build.buildsetid)
        log.debug("Created %i properties" % r.rowcount)

        # Create a new build request
        q = text("""INSERT INTO buildrequests
                (`buildsetid`, `buildername`, `submitted_at`, `priority`, `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`, `complete`, `results`, `complete_at`)
                VALUES
                (:buildsetid, :buildername, :submitted_at, 0, 0, 0, NULL, 0, NULL, NULL)""")
        log.debug(q)

        r = self.db.execute(q,
                buildsetid=buildsetid,
                buildername=build.buildername,
                submitted_at=now,
                )

        new_brid = r.lastrowid
        log.debug("Created buildrequest %s", new_brid)
        return {"errors": False, "msg": "Ok"}

    def do_rebuild_request(self, message_data, message):
        who = message_data['who']
        brid = message_data['body']['brid']
        log.info("rebuilding request by %s of %s", who, brid)

        # Get the build request and build set
        request = self.db.execute(text("""\
                SELECT * FROM
                    buildrequests, buildsets WHERE
                    buildrequests.id=:brid AND
                    buildrequests.buildsetid = buildsets.id"""),
            brid=brid).fetchone()

        if not request:
            log.info("No request with id %s, giving up" % brid)
            return {"errors": True, "msg": "No request with that id"}

        # Create a new buildset
        q = text("""INSERT INTO buildsets
            (`external_idstring`, `reason`, `sourcestampid`, `submitted_at`, `complete`, `complete_at`, `results`)
            VALUES
            (:idstring, :reason, :sourcestampid, :submitted_at, 0, NULL, NULL)""")
        log.debug(q)

        now = time.time()
        r = self.db.execute(q,
                idstring=request.external_idstring,
                reason='Rebuilt by %s' % who,
                sourcestampid=request.sourcestampid,
                submitted_at=now,
                )

        buildsetid = r.lastrowid
        log.debug("Created buildset %s", buildsetid)

        # Copy buildset properties
        q = text("""INSERT INTO buildset_properties
                (`buildsetid`, `property_name`, `property_value`)
                SELECT :buildsetid, `property_name`, `property_value` FROM
                    buildset_properties WHERE
                    buildsetid = :oldbsid""")
        log.debug(q)
        r = self.db.execute(q,
                buildsetid=buildsetid,
                oldbsid=request.buildsetid)
        log.debug("Created %i properties" % r.rowcount)

        # Create a new build request
        q = text("""INSERT INTO buildrequests
                (`buildsetid`, `buildername`, `submitted_at`, `priority`, `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`, `complete`, `results`, `complete_at`)
                VALUES
                (:buildsetid, :buildername, :submitted_at, 0, 0, 0, NULL, 0, NULL, NULL)""")
        log.debug(q)

        r = self.db.execute(q,
                buildsetid=buildsetid,
                buildername=request.buildername,
                submitted_at=now,
                )

        new_brid = r.lastrowid
        log.debug("Created buildrequest %s", new_brid)
        return {"errors": False, "msg": "Ok"}

    def do_cancel_build(self, message_data, message):
        who = message_data['who']
        build_id = message_data['body']['bid']
        log.info("cancelling build by %s of %s", who, build_id)

        # Check that the build is still active
        build = self.db.execute(text("""
            SELECT * FROM buildrequests, builds WHERE
                builds.brid=buildrequests.id AND
                builds.id = :build_id"""), build_id=build_id).fetchone()

        if not build:
            log.info("No build with id %s, giving up" % build_id)
            return {"errors": True, "msg": "No build with that id"}

        if build.complete_at and build.complete:
            log.info("build is complete, nothing to do")
            return {"errors": False, "msg": "Build is complete, nothing to do"}

        if build.claimed_at:
            log.info("build is running, going to cancel it!")
            cancel_url = self._get_cancel_url(build.claimed_by_name, build.buildername, build.number)
            log.debug("Cancelling at %s", cancel_url)
            try:
                self._cancel_build(build.claimed_by_name, build.buildername, build.number, who, "Cancelled via self-serve")
                return {"errors": False, "msg": "Ok"}
            except:
                log.exception("Couldn't cancel build")
                return {"errors": True, "msg": "Error cancelling build"}

        # Not sure how we get here...
        log.warn("Build %i has no claimed_at" % build_id)
        return {"errors": True, "msg": "Error cancelling build"}

    def do_new_build_at_revision(self, message_data, message):
        who = message_data['who']
        branch = message_data['body']['branch']
        revision = message_data['body']['revision']
        log.info("New build by %s of %s %s", who, branch, revision)

        pb_url = self._get_master_pb(self.sendchange_master)

        repo_path = self._get_repo_path(branch)
        revlink = self._get_revlink(branch, revision)

        cmd = [self.buildbot, 'sendchange', '--master', pb_url, '--branch',
                repo_path, '--revision', revision, '--revlink', revlink,
                '--user', who, '--comments', 'Submitted via self-serve',
                'dummy']
        log.info("Running %s", cmd)
        subprocess.check_call(cmd)
        return {"errors": False, "msg": "Ok"}


if __name__ == '__main__':
    import os
    from optparse import OptionParser
    from ConfigParser import RawConfigParser

    from carrot.connection import AMQPConnection
    from sqlalchemy import create_engine

    from buildapi.lib.mq import JobRequestConsumer, JobRequestDonePublisher

    parser = OptionParser()
    parser.set_defaults(
            configfile='selfserve-agent.ini',
            wait=False,
            verbosity=log.INFO
            )
    parser.add_option("-w", "--wait", dest="wait", action="store_true")
    parser.add_option("-v", dest="verbosity", action="store_const", const=log.DEBUG, help="be verbose")
    parser.add_option("-q", dest="verbosity", action="store_const", const=log.WARN, help="be quiet")
    parser.add_option("-f", "--config-file", dest="configfile")

    options, args = parser.parse_args()

    if not os.path.exists(options.configfile):
        parser.error("Config file %s does not exist" % options.configfile)

    log.basicConfig(format='%(asctime)s %(message)s', level=options.verbosity)

    config = RawConfigParser(
            {'port': 5672,
             'ssl': 'false',
             'vhost': '/',
             })
    config.read([options.configfile])

    amqp_exchange = config.get('carrot', 'exchange')

    amqp_conn = AMQPConnection(
            hostname=config.get('carrot', 'hostname'),
            userid=config.get('carrot', 'userid'),
            password=config.get('carrot', 'password'),
            port=config.getint('carrot', 'port'),
            ssl=config.getboolean('carrot', 'ssl'),
            virtual_host=config.get('carrot', 'vhost'),
            )

    branch_map = {}
    for section in config.sections():
        if not section.startswith('branch:'):
            continue
        branch = section.split(':', 1)[1]
        repo_path = config.get(section, 'repo_path')
        revlink = config.get(section, 'revlink')

        branch_map[branch] = BranchInfo(repo_path=repo_path, revlink=revlink)

    agent = BuildAPIAgent(
            db=create_engine(config.get('db', 'url'), pool_recycle=60),
            masters_url=config.get('masters', 'masters-url'),
            buildbot=config.get('masters', 'buildbot'),
            sendchange_master=config.get('masters', 'sendchange-master'),
            publisher=JobRequestDonePublisher(amqp_conn, exchange=amqp_exchange),
            branch_map=branch_map,
            )

    consumer = JobRequestConsumer(amqp_conn, exchange=amqp_exchange, queue=config.get('carrot', 'queue'))
    consumer.register_callback(agent.receive_message)

    if options.wait:
        try:
            consumer.wait()
        except KeyboardInterrupt:
            # Let this go without a fuss
            pass
    else:
        while True:
            message = consumer.fetch(enable_callbacks=True)
            if not message:
                break
