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
import socket

from sqlalchemy import text
from sqlalchemy.exc import TimeoutError

from buildapi.lib import json

HOSTNAME = socket.gethostname()


class NoRedirects(urllib2.HTTPErrorProcessor):
    "Helper class that eats HTTP 302 redirects so we don't follow redirects"
    def http_response(self, request, response):
        if response.code == 302:
            return response
        return urllib2.HTTPErrorProcessor.http_response(self, request, response)


noredirect_opener = urllib2.build_opener(NoRedirects)


def get_buildernames(branch, builders, builder_expression,
                     builder_exclusions=None):
    # Filter the builders by this specific branch first
    names = [buildername for (buildername, builder) in builders.iteritems() if
             builder['properties'].get('branch') == branch]
    # Then apply the builder expression and exclusions
    names = [b for b in names if re.search(builder_expression, b)]
    if builder_exclusions:
        names = [b for b in names if not
                 any(re.search(e, b) for e in builder_exclusions)]
    return names


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
    def __init__(self, db, masters_url, buildbot, sendchange_master, publisher,
                 branches_url, allthethings_url, clobberer_url,
                 clobberer_auth=None):
        self.db = db
        self.masters_url = masters_url
        self.branches_url = branches_url
        self.allthethings_url = allthethings_url
        self.clobberer_url = clobberer_url
        self.clobberer_auth = clobberer_auth
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
                self.masters = json.load(urllib2.urlopen(self.masters_url, timeout=30))
                log.info("Loading branches from %s", self.branches_url)
                self.branches = json.load(urllib2.urlopen(self.branches_url, timeout=30))
                log.info("Loading builders from %s", self.allthethings_url)
                self.builders = json.load(urllib2.urlopen(self.allthethings_url, timeout=30))['builders']
                self._last_refresh = time.time()
            except:
                log.exception("Couldn't load data; using old ones")

    def _get_repo_path(self, branch):
        # branches[branch]['repo'] is a string like "https://hg.mozilla.org/projects/foo"
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
        data = urllib2.urlopen(build_url, timeout=30).read()
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

    def _authorize(self, req, token):
        if token:
            log.debug('Authorising request')
            req.add_unredirected_header(
                'Authorization', 'Bearer %s' % (token))
        else:
            log.debug('No token supplied, skipping authorization')

    def _clobber_slave(self, slavename, builder_name):
        data = [{
            "slave": slavename,
            "buildername": builder_name
        }]
        log.info("Clobbering %s %s at %s %s", slavename, builder_name, self.clobberer_url, data)
        req = urllib2.Request(self.clobberer_url)
        req.add_header('Content-Type', 'application/json')
        self._authorize(req, self.clobberer_auth)
        return urllib2.urlopen(req, json.dumps(data))

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
            if 'body' not in message_data or 'request_id' not in message_data['body']:
                log.warning("discarding malformed message - no request_id")
                message.ack()
                return
            retval = action_func(message_data, message)
            msg = {'body': retval}
            msg['request_id'] = message_data['body']['request_id']
            self.publisher.ack_msg(msg)
            message.ack()
        except TimeoutError:
            log.exception("TimeoutError accessing the DB pool")
            raise
        except:
            # Send a failure message
            log.exception("Error processing message; logging failure and acking")
            msg = {'body': {"errors": True, "msg":
                            "there was an error processing your request; please "
                            "check logs on %s" % HOSTNAME}}
            msg['request_id'] = message_data['body']['request_id']
            self.publisher.ack_msg(msg)
            message.ack()

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
        count = message_data['body'].get('count', 1)
        priority = message_data['body'].get('priority', 0)
        log.info("rebuilding build by %s of %s count %s pri %s", who, bid, count, priority)

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

        now = time.time()
        for i in range(count):
            # Create a new buildset
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
                    (`buildsetid`, `buildername`, `submitted_at`, `priority`,
                     `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`,
                     `complete`, `results`, `complete_at`)
                    VALUES
                     (:buildsetid, :buildername, :submitted_at, :priority,
                      0, NULL, NULL,
                      0, NULL, NULL)""")
            log.debug(q)

            r = self.db.execute(
                q,
                buildsetid=buildsetid,
                buildername=build.buildername,
                submitted_at=now,
                priority=priority,
            )

            new_brid = r.lastrowid
            log.debug("Created buildrequest %s", new_brid)
        return {"errors": False, "msg": "Ok"}

    def do_rebuild_request(self, message_data, message):
        who = message_data['who']
        brid = message_data['body']['brid']
        count = message_data['body'].get('count', 1)
        priority = message_data['body'].get('priority', 0)
        log.info("rebuilding request by %s of %s count %s pri %s", who, brid, count, priority)

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

        now = time.time()
        for i in range(count):
            # Create a new buildset
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
                    (`buildsetid`, `buildername`, `submitted_at`, `priority`,
                     `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`,
                     `complete`, `results`, `complete_at`)
                    VALUES
                     (:buildsetid, :buildername, :submitted_at, :priority,
                      0, NULL, NULL,
                      0, NULL, NULL)""")
            log.debug(q)

            r = self.db.execute(
                q,
                buildsetid=buildsetid,
                buildername=request.buildername,
                submitted_at=now,
                priority=priority,
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

    def _create_build_for_revision(self, who, branch, revision, priority,
                                   builder_expression,
                                   builder_exclusions=None):
        now = time.time()
        repo_path = self._get_repo_path(branch)

        # Figure out our set of builders
        buildernames = get_buildernames(branch, self.builders,
                                        builder_expression, builder_exclusions)
        log.debug("buildernames are %s", buildernames)
        if not buildernames:
            log.info("no builders found")
            return {"errors": False, "msg": "No builds to create"}

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
            " pgo-build$",
        )

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
            " nightly$",
            ['l10n'],
        )

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

    def do_new_build_for_builder(self, message_data, message):
        who = message_data['who']
        branch = message_data['body']['branch']
        revision = message_data['body']['revision']
        priority = message_data['body']['priority']
        builder_name = message_data['body']['builder_name']
        files = message_data['body']['files']
        log.info("New build for %s by %s of %s %s", builder_name, who, branch, revision)

        # Create a sourcestamp
        real_branch = branch.split("-selfserve")[0]
        q = text("""INSERT INTO sourcestamps
                (`branch`, `revision`, `patchid`, `repository`, `project`)
                VALUES
                (:real_branch, :revision, NULL, '', '')
                """)
        log.debug(q)
        r = self.db.execute(q, real_branch=real_branch, revision=revision)
        ssid = r.lastrowid  # SourcestampID
        log.debug("Created sourcestamp %s", ssid)

        # Create change object
        when = time.time()
        q = text("""INSERT INTO changes
                (`author`, `comments`, `is_dir`, `branch`,
                `revision`, `revlink`, `when_timestamp`, `category`,
                `repository`, `project`)
                VALUES
                (:who, '', 0, :branch, :revision, NULL, :when, NULL, '', '')
                """)
        log.debug(q)
        r = self.db.execute(q, who=who, branch=branch, revision=revision, when=when)
        cid = r.lastrowid
        log.debug("Created change %s", cid)

        # Create change-files
        for f in files:
            q = text("""INSERT INTO change_files
                    (`changeid`, `filename`)
                    VALUES
                    (:cid, :f)
                    """)
            log.debug(q)
            r = self.db.execute(q, cid=cid, f=f)
        log.debug("Created change_file for change object %s", cid)

        # Create sourcestamp_changes
        q = text("""INSERT INTO sourcestamp_changes
                (`sourcestampid`, `changeid`)
                VALUES
                (:ssid, :cid)
                """)
        log.debug(q)
        r = self.db.execute(q, ssid=ssid, cid=cid)
        log.debug("Created sourcestamp_changes for sourcestamp %s, change object %s", ssid, cid)

        # Create a new buildset
        now = time.time()
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
        # Making a tuple of each key and a tuple of it's associated property and the source "self-serve"
        props.update(((k, json.dumps((v, "self-serve"))) for (k, v) in message_data['body']['properties'].iteritems()))
        log.debug(q)
        for key, value in props.items():
            r = self.db.execute(q, buildsetid=buildsetid, key=key, value=value)
            log.debug("Created buildset_property %s=%s", key, value)

        # Create buildrequests
        q = text("""INSERT INTO buildrequests
                (`buildsetid`, `buildername`, `submitted_at`, `priority`, `claimed_at`, `claimed_by_name`, `claimed_by_incarnation`, `complete`, `results`, `complete_at`)
                VALUES
                (:buildsetid, :builder_name, :submitted_at, :priority, 0, NULL, NULL, 0, NULL, NULL)""")
        log.debug(q)
        r = self.db.execute(
            q,
            buildsetid=buildsetid,
            builder_name=builder_name,
            submitted_at=now,
            priority=priority)
        log.debug("Created buildrequest %s: %i", builder_name, r.lastrowid)
        return {"errors": False, "msg": "Ok"}


def main():
    import os
    from optparse import OptionParser
    from ConfigParser import RawConfigParser

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

    amqp_config = {}
    for option in config.options('mq'):
        amqp_config['mq.%s' % option] = config.get('mq', option)

    agent = BuildAPIAgent(
        db=create_engine(config.get('db', 'url'), pool_recycle=60),
        masters_url=config.get('masters', 'masters-url'),
        buildbot=config.get('masters', 'buildbot'),
        sendchange_master=config.get('masters', 'sendchange-master'),
        publisher=JobRequestDonePublisher(amqp_config),
        branches_url=config.get('branches', 'url'),
        allthethings_url=config.get('allthethings', 'url'),
        clobberer_url=config.get('clobberer', 'url'),
        clobberer_auth=config.get('clobberer', 'auth'),
    )

    consumer = JobRequestConsumer(amqp_config)
    consumer.register_callback(agent.receive_message)

    if options.wait:
        try:
            consumer.run()
        except KeyboardInterrupt:
            # Let this go without a fuss
            pass
    else:
        consumer.run_until_idle()


if __name__ == '__main__':
    main()
