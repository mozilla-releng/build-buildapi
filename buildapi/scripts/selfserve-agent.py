#!/usr/bin/python
"""selfserve-agent.py [options]

Gets any messages and executes them."""
import logging as log
import time
import urllib
import urllib2
from urlparse import urlparse
import subprocess
import uuid
import re

from sqlalchemy import text
from sqlalchemy.exc import TimeoutError

from buildapi.lib import json


class NoRedirects(urllib2.HTTPErrorProcessor):
    "Helper class that eats HTTP 302 redirects so we don't follow redirects"
    def http_response(self, request, response):
        if response.code == 302:
            return response
        return urllib2.HTTPErrorProcessor.http_response(self, request, response)

noredirect_opener = urllib2.build_opener(NoRedirects)


def genBuildID(now=None):
    """Return a buildid based on the current time"""
    if not now:
        now = time.time()
    return time.strftime("%Y%m%d%H%M%S", time.localtime(now))


def genBuildUID():
    """Return a unique build uid"""
    return uuid.uuid4().hex


def create_buildset(db, idstring, reason, ssid, submitted_at):
    q = text("""INSERT INTO buildsets
        (`external_idstring`, `reason`, `sourcestampid`, `submitted_at`, `complete`, `complete_at`, `results`)
        VALUES
        (:idstring, :reason, :sourcestampid, :submitted_at, 0, NULL, NULL)""")
    log.debug(q)

    r = db.execute(q,
                   idstring=idstring,
                   reason=reason,
                   sourcestampid=ssid,
                   submitted_at=submitted_at,
                   )
    buildsetid = r.lastrowid
    log.debug("Created buildset %s", buildsetid)
    return buildsetid


class BuildAPIAgent:
    def __init__(self, db, masters_url, buildbot, sendchange_master, publisher, branches_url, clobberer_url):
        self.db = db
        self.masters_url = masters_url
        self.branches_url = branches_url
        self.clobberer_url = clobberer_url
        self.buildbot = buildbot
        self.sendchange_master = sendchange_master
        self.publisher = publisher
        self.branches = {}
        self.masters = []

        self._last_refresh = 0

    def _refresh(self):
        # Refresh every 5 minutes
        if time.time() - self._last_refresh > 300:
            try:
                log.info("Loading masters from %s", self.masters_url)
                self.masters = json.load(urllib.urlopen(self.masters_url))
                log.info("Loading branches from %s", self.branches_url)
                self.branches = json.load(urllib.urlopen(self.branches_url))
                self._last_refresh = time.time()
            except:
                log.exception("Couldn't load data; using old ones")

    def _get_repo_path(self, branch):
        # branches[branch]['repo'] is a string like "http://hg.mozilla.org/projects/foo"
        # use urlparse to get the path out of that ("/projects/foo"), and remove
        # the leading / to be left with "projects/foo"
        return urlparse(self.branches[branch]['repo']).path.lstrip("/")

    def _get_revlink(self, branch, revision):
        repo_path = self.branches[branch]['repo']
        return "%s/rev/%s" % (repo_path, revision)

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

    def _get_slave_name(self, claimed_by_name, builder_name, build_number):
        build_url = self._get_build_url(claimed_by_name, builder_name, build_number)
        # Fetch the build url
        log.info("getting slavename from  %s", build_url)
        data = urllib.urlopen(build_url).read()
        # scraping alert!
        # the build page has strings like
        # <a href="../../../buildslaves/$slavename">$slavename</a>
        # we want to extract the slave name from this
        m = re.search(r'''href=['"].*/buildslaves/(\S+)['"]''', data)
        if m:
            slavename = m.group(1)
            return slavename

    def _get_cancel_url(self, claimed_by_name, builder_name, build_number):
        build_url = self._get_build_url(claimed_by_name, builder_name, build_number)
        return "%s/stop" % build_url

    def _clobber_slave(self, slavename, builder_name):
        data = urllib.urlencode({
            "slave-%s" % slavename: builder_name,
            "form_submitted": "1",
        })
        log.info("Clobbering %s %s at %s %s", slavename, builder_name, self.clobberer_url, data)

        urllib.urlopen(self.clobberer_url, data)

    def _can_cancel_build(self, claimed_by_name, builder_name, build_number, who, comments):
        unstoppable = []
        for u in unstoppable:
            if u in builder_name:
                return False
        return True

    def _should_clobber_build(self, builder_name):
        """Return True if this builder needs to be clobbered via clobberer when a
        build is cancelled via self-serve"""
        # Generally the following don't need clobbering:
        # * try builds
        # * nightly builds
        # * tests
        # This doesn't have to be perfect. If we return True incorrectly, we
        # need to load the buildbot page to figure out which slave is doing a
        # job, but the subsequent clobber is a noop.
        dont_clobber = ['nightly', ' try ', '_try_', 'talos', 'pgo test', 'opt test', 'debug test']
        for c in dont_clobber:
            if c in builder_name:
                return False
        return True

    def _cancel_build(self, claimed_by_name, builder_name, build_number, who, comments):
        cancel_url = self._get_cancel_url(claimed_by_name, builder_name, build_number)
        if not self._can_cancel_build(claimed_by_name, builder_name, build_number, who, comments):
            log.info("Not stopping unstoppable build at %s", cancel_url)
            return "Not stopping unstoppable build"

        if self._should_clobber_build(builder_name):
            slavename = self._get_slave_name(claimed_by_name, builder_name, build_number)
            if slavename:
                # Clobber
                self._clobber_slave(slavename, builder_name)

        # Stop the build on buildbot
        data = urllib.urlencode({
            "comments": comments,
            "username": who,
        })
        log.info("Cancelling at %s", cancel_url)
        # Use the noredirect_opener so we don't follow the 302 to the builder
        # page
        noredirect_opener.open(cancel_url, data)
        return "Ok"

    def _cancel_request(self, who, request):
        brid = request.id
        log.info("cancelling request by %s of %s", who, brid)

        # Check that the request is still active
        request = self.db.execute(text("SELECT * FROM buildrequests WHERE id=:brid"), brid=brid).fetchone()

        if request.complete_at and request.complete:
            log.info("request is complete, nothing to do")
            return {"errors": False, "msg": "Request %i is complete, nothing to do" % brid}

        if request.claimed_at:
            log.info("request is running, going to cancel it!")
            build = self.db.execute(text("SELECT * from builds where brid=:brid and finish_time is null"), brid=brid).fetchone()
            try:
                msg = self._cancel_build(request.claimed_by_name, request.buildername, build.number, who, "Cancelled via self-serve")
                return {"errors": False, "msg": "%i: %s" % (brid, msg)}
            except:
                log.exception("Couldn't cancel build")
                return {"errors": True, "msg": "Error cancelling build (request %i)" % brid}

        log.info("request is pending, going to cancel it")
        now = time.time()
        result = self.db.execute(text("UPDATE buildrequests SET complete=1, results=2, complete_at=:now WHERE id=:brid"),
                                 brid=brid,
                                 now=now,
                                 )
        log.debug("updated DB: %i", result.rowcount)
        if result.rowcount != 1:
            return {"errors": True, "msg": "Error cancelling request %i: %i rows affected" % (brid, result.rowcount)}
        return {"errors": False, "msg": "%i: Ok" % brid}

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

        self._refresh()

        try:
            retval = action_func(message_data, message)
            msg = {'body': retval}
            msg['request_id'] = message_data['body']['request_id']
            self.publisher.ack_msg(msg)
            message.ack()
        except TimeoutError:
            log.exception("TimeoutError accessing the DB pool, exiting...")
            raise SystemExit(1)
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

        # Check that the request is still active
        request = self.db.execute(text("SELECT * FROM buildrequests WHERE id=:brid"), brid=brid).fetchone()

        if not request:
            log.info("No request with id %s, giving up" % brid)
            return {"errors": True, "msg": "No request with that id"}

        return self._cancel_request(who, request)

    def do_rebuild_build(self, message_data, message):
        who = message_data['who']
        bid = message_data['body']['bid']
        log.info("rebuilding build by %s of %s", who, bid)

        # Get the build request and build set
        build = self.db.execute(text(
            """SELECT * FROM
                    buildrequests, buildsets, builds WHERE
                    builds.id=:bid AND
                    builds.brid = buildrequests.id AND
                    buildrequests.buildsetid = buildsets.id"""
        ), bid=bid).fetchone()

        if not build:
            log.info("No build with id %s, giving up" % bid)
            return {"errors": True, "msg": "No build with that id"}

        # Create a new buildset
        now = time.time()
        buildsetid = create_buildset(
            self.db,
            idstring=build.external_idstring,
            reason='Self-serve: Rebuilt by %s' % who,
            ssid=build.sourcestampid,
            submitted_at=now,
        )

        # Copy buildset properties
        q = text("""INSERT INTO buildset_properties
                (`buildsetid`, `property_name`, `property_value`)
                SELECT :buildsetid, `property_name`, `property_value` FROM
                    buildset_properties WHERE
                    buildsetid = :oldbsid""")
        log.debug(q)
        r = self.db.execute(
            q,
            buildsetid=buildsetid,
            oldbsid=build.buildsetid)
        log.debug("Created %i properties" % r.rowcount)

        # Create a new build request
        q = text("""INSERT INTO buildrequests
                (`buildsetid`, `buildername`, `submitted_at`, `priority`, `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`, `complete`, `results`, `complete_at`)
                VALUES
                (:buildsetid, :buildername, :submitted_at, 0, 0, NULL, NULL, 0, NULL, NULL)""")
        log.debug(q)

        r = self.db.execute(
            q,
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
        request = self.db.execute(text(
            """SELECT * FROM
                    buildrequests, buildsets WHERE
                    buildrequests.id=:brid AND
                    buildrequests.buildsetid = buildsets.id"""),
            brid=brid).fetchone()

        if not request:
            log.info("No request with id %s, giving up" % brid)
            return {"errors": True, "msg": "No request with that id"}

        # Create a new buildset
        now = time.time()
        buildsetid = create_buildset(
            self.db,
            idstring=request.external_idstring,
            reason='Self-serve: Rebuilt by %s' % who,
            ssid=request.sourcestampid,
            submitted_at=now,
        )

        # Copy buildset properties
        q = text("""INSERT INTO buildset_properties
                (`buildsetid`, `property_name`, `property_value`)
                SELECT :buildsetid, `property_name`, `property_value` FROM
                    buildset_properties WHERE
                    buildsetid = :oldbsid""")
        log.debug(q)
        r = self.db.execute(
            q,
            buildsetid=buildsetid,
            oldbsid=request.buildsetid)
        log.debug("Created %i properties" % r.rowcount)

        # Create a new build request
        q = text("""INSERT INTO buildrequests
                (`buildsetid`, `buildername`, `submitted_at`, `priority`, `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`, `complete`, `results`, `complete_at`)
                VALUES
                (:buildsetid, :buildername, :submitted_at, 0, 0, NULL, NULL, 0, NULL, NULL)""")
        log.debug(q)

        r = self.db.execute(
            q,
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
            try:
                msg = self._cancel_build(build.claimed_by_name, build.buildername, build.number, who, "Cancelled via self-serve")
                return {"errors": False, "msg": msg}
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

    def _create_build_for_revision(self, who, branch, revision, priority, builder_expression, builder_exclusions=None):
        if builder_exclusions is None:
            builder_exclusions = ['%l10n nightly']
        now = time.time()
        repo_path = self._get_repo_path(branch)

        # Find builders that have been active in the past 2 weeks
        q = """SELECT DISTINCT buildername FROM buildrequests WHERE
                buildername LIKE :buildername AND
            """
        for i, bx in enumerate(builder_exclusions):
            q = q + "buildername NOT LIKE :buildername_exclusion_%i AND " % i
        q = q + """
          submitted_at > :submitted_at"""
        qparams = {
            'buildername': builder_expression,
            'submitted_at': time.time() - 14 * 24 * 3600,
        }
        for i, bx in enumerate(builder_exclusions):
            qparams['buildername_exclusion_%i' % i] = builder_exclusions[i]
        result = self.db.execute(text(q), qparams)

        buildernames = [r[0] for r in result]
        log.debug("buildernames are %s", buildernames)

        # Create a sourcestamp
        q = text("""INSERT INTO sourcestamps
                (`branch`, `revision`, `patchid`, `repository`, `project`)
                VALUES
                (:branch, :revision, NULL, '', '')
                """)
        log.debug(q)
        r = self.db.execute(q, branch=repo_path, revision=revision)
        ssid = r.lastrowid
        log.debug("Created sourcestamp %s", ssid)

        # Create a new buildset
        buildsetid = create_buildset(
            self.db,
            idstring=None,
            reason='Self-serve: Requested by %s' % who,
            ssid=ssid,
            submitted_at=now,
        )

        # Create buildset properties (buildid, builduid)
        q = text("""INSERT INTO buildset_properties
                (`buildsetid`, `property_name`, `property_value`)
                VALUES
                (:buildsetid, :key, :value)
                """)
        props = {
            'buildid': json.dumps((genBuildID(now), "self-serve")),
            'builduid': json.dumps((genBuildUID(), "self-serve")),
        }
        log.debug(q)
        for key, value in props.items():
            r = self.db.execute(q, buildsetid=buildsetid, key=key, value=value)
            log.debug("Created buildset_property %s=%s", key, value)

        # Create buildrequests
        q = text("""INSERT INTO buildrequests
                (`buildsetid`, `buildername`, `submitted_at`, `priority`, `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`, `complete`, `results`, `complete_at`)
                VALUES
                (:buildsetid, :buildername, :submitted_at, :priority, 0, NULL, NULL, 0, NULL, NULL)""")
        log.debug(q)
        for buildername in buildernames:
            r = self.db.execute(
                q,
                buildsetid=buildsetid,
                buildername=buildername,
                submitted_at=now,
                priority=priority)
            log.debug("Created buildrequest %s: %i", buildername, r.lastrowid)
        return {"errors": False, "msg": "Ok"}

    def do_new_pgobuild_at_revision(self, message_data, message):
        who = message_data['who']
        branch = message_data['body']['branch']
        revision = message_data['body']['revision']
        priority = message_data['body']['priority']
        log.info("New PGO build by %s of %s %s", who, branch, revision)
        return self._create_build_for_revision(
            who,
            branch,
            revision,
            priority,
            "%% %s pgo-build" % branch)

    def do_new_nightly_at_revision(self, message_data, message):
        who = message_data['who']
        branch = message_data['body']['branch']
        revision = message_data['body']['revision']
        priority = message_data['body']['priority']
        log.info("New nightly by %s of %s %s", who, branch, revision)
        return self._create_build_for_revision(
            who,
            branch,
            revision,
            priority,
            '%' + branch + '%nightly',
            ['%' + branch + '_v%nightly', '%l10n nightly'])

    def do_cancel_revision(self, message_data, message):
        who = message_data['who']
        branch = message_data['body']['branch']
        revision = "%s%%" % message_data['body']['revision'][:12]
        prefixbranch = "%s%%" % branch
        suffixbranch = "%%%s" % branch

        q = text("""SELECT buildrequests.*
                    FROM
                        buildrequests, buildsets, sourcestamps
                    WHERE
                        buildrequests.buildsetid = buildsets.id AND
                        buildsets.sourcestampid = sourcestamps.id AND
                        sourcestamps.revision LIKE :revision AND
                        buildrequests.complete = 0 AND
                        (sourcestamps.branch LIKE :prefixbranch OR
                         sourcestamps.branch LIKE :suffixbranch)
                """)
        requests = self.db.execute(q, revision=revision, prefixbranch=prefixbranch, suffixbranch=suffixbranch)

        msgs = []
        errors = False
        for request in requests:
            result = self._cancel_request(who, request)
            if result['errors']:
                errors = True
            msgs.append(result['msg'])
        return {"errors": errors, "msg": "\n".join(msgs)}


def main():
    import os
    from optparse import OptionParser
    from ConfigParser import RawConfigParser

    from sqlalchemy import create_engine

    from buildapi.lib.mq import JobRequestConsumer, JobRequestDonePublisher, amqp_connection_from_config

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

    amqp_config = {}

    for option in config.options('carrot'):
        if option == 'ssl':
            amqp_config['carrot.%s' % option] = config.getboolean('carrot', option)
        else:
            amqp_config['carrot.%s' % option] = config.get('carrot', option)

    amqp_exchange = config.get('carrot', 'exchange')
    amqp_conn = amqp_connection_from_config(amqp_config, 'carrot')

    agent = BuildAPIAgent(
        db=create_engine(config.get('db', 'url'), pool_recycle=60),
        masters_url=config.get('masters', 'masters-url'),
        buildbot=config.get('masters', 'buildbot'),
        sendchange_master=config.get('masters', 'sendchange-master'),
        publisher=JobRequestDonePublisher(amqp_config, 'carrot'),
        branches_url=config.get('branches', 'url'),
        clobberer_url=config.get('clobberer', 'url'),
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

if __name__ == '__main__':
    main()
