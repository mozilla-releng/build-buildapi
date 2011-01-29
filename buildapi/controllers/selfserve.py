import logging

from datetime import datetime

from webhelpers.util import html_escape as e
from sqlalchemy.orm.session import Session

from pylons import request, response, tmpl_context as c, config, \
    app_globals as g
from pylons.controllers.util import abort, redirect
from pylons.decorators.cache import beaker_cache

import formencode
from formencode import validators

from buildapi.lib.base import BaseController, render
from buildapi.model.builds import getBuild, getRequest, getBuildsForUser
from buildapi.model.buildapidb import JobRequest
from buildapi.lib.helpers import get_builders, url
from buildapi.lib import json, times

log = logging.getLogger(__name__)
access_log = logging.getLogger("buildapi.access")

IntValidator = validators.Int(not_empty=True)

class SelfserveController(BaseController):
    """
    Informational Requests
    ----------------------
    Results are formatted according to the 'format' query parameter
    ("?format=html" or "?format=json").  If 'format' is not set, and the
    'Accept' header of the request includes 'application/json', the format will
    be set to json.  Otherwise the format will be html.

    Will return HTTP 200 for successful queries, or HTTP 404 if a resource is
    not found.

    Job Requests
    ------------
    PUT, POST, and DELETE requests (which can be faked by setting a '_method'
    field to 'PUT' or 'DELETE' in a regular POST request if your client doesn't
    support PUT/DELETE easiliy) represent requests to change buildbot state.
    These are called "Job Requests".

    Requests to these methods return a job status dictionary, which includes
    the following keys:
        "status"     - "OK" or "FAILED"
        "msg"        - informational text
        "request_id" - the job request id.  You can find the status of the job
                       by visiting /self-serve/jobs/{job_id}.  This is only set for
                       successfull requests.

    Job requests can return 202 (HTTP Accepted) if the request was accepted, or
    503 (HTTP Service Unavailable) if there was an error.  In case of a 503
    error, the request should be re-submitted at a later time.

    Missing or bad parameters for the request type will result in a 400 error.
    """
    def _htmlify(self, obj):
        return "<pre>%s</pre>" % e(json.dumps(obj, indent=2))

    def _format(self, obj):
        if self._fmt == 'json':
            return self.jsonify(obj)
        else:
            return self._htmlify(obj)

    def _ok(self, obj, status=200):
        response.status = status
        #obj['status'] = "OK"
        c.raw_data = obj
        retval = self._format(obj)
        if self._fmt == 'json':
            # Disable redirecting to the Error middleware
            request.environ['pylons.status_code_redirect'] = True
            return retval
        elif self._fmt == 'html':
            c.data = obj
            c.formatted_data = retval
            action = request.environ['pylons.routes_dict']['action']
            template = '/self-serve/%s.mako' % action
            if g.mako_lookup.has_template(template):
                return render(template)
            else:
                return retval

    def _failed(self, msg, status):
        response.status = status
        obj = {'msg': msg}
        obj['status'] = "FAILED"
        retval = self._format(obj)
        if self._fmt == 'json':
            # Disable redirecting to the Error middleware
            request.environ['pylons.status_code_redirect'] = True
        return retval

    def _format_mq_response(self, msg):
        retval = self._format(msg)
        if msg['status'] == 'OK':
            if self._fmt == 'html' and 'request_id' in msg:
                # Redireect to the job_status view
                return redirect(url('job_status', job_id=msg['request_id']))
            response.status = 202
            return retval
        else:
            response.status = 503
            return retval

    def _require_auth(self):
        who = None

        if config.get('auth_override'):
            who = config['auth_override']
            log.warn("Overriding auth for %s" % who)
        elif 'X-Remote-User' in request.headers:
            who = request.headers['X-Remote-User']
        else:
            who = request.remote_user

        if not who:
            abort(403, "ACCESS DENIED!")

        access_log.info("%s accessing %s %s", who, request.method,
                request.path_info)
        return who

    @beaker_cache(query_args=True)
    def index(self):
        """Root of the API.  You're looking at it!"""
        routes = []
        for route in config['routes.map'].matchlist:
            controller = route.defaults.get('controller')
            if controller != 'selfserve':
                continue

            if route.conditions:
                method = route.conditions.get('method')[0]
            else:
                method = 'GET'

            action = route.defaults.get('action')
            docstring = getattr(self, action).__doc__

            routes.append( (route.routepath, method, docstring) )
        routes.sort()
        c.main_docstring = self.__doc__
        c.routes = routes
        return render('/self-serve/index.mako')

    @beaker_cache(query_args=True)
    def branches(self):
        """Return a list of all the branches"""
        return self._format(config['branches'])

    def branch(self, branch):
        """Return a list of builds running on this branch"""
        # TODO: start/enddates

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)
        else:
            today = times.now(g.tz).replace(hour=0, minute=0, second=0,
                    microsecond=0)
            date = request.params.get('date')
            if date:
                date = g.tz.localize(datetime.strptime(date, '%Y-%m-%d'))
            else:
                date = today
            c.date = date
            c.today = today
            builds = g.buildapi_cache.get_builds_for_day(date, branch)
            return self._ok(builds)

    def build(self, branch, build_id):
        """Return information about a build"""
        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        retval = getBuild(branch, build_id)
        if not retval:
            return self._failed("Build %s not found on branch %s" %
                    (build_id, branch), 404)

        return self._ok(retval)

    def request(self, branch, request_id):
        """Return information about a request"""
        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        retval = getRequest(branch, request_id)
        if not retval:
            return self._failed("Request %s not found on branch %s" %
                    (request_id, branch), 404)

        return self._ok(retval)

    def revision(self, branch, revision):
        """Return a list of builds running for this revision"""
        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        retval = g.buildapi_cache.get_builds_for_revision(branch, revision)
        if not retval:
            return self._failed("Revision %s not found on branch %s" %
                    (revision, branch), 404)

        return self._ok(retval)

    @beaker_cache(query_args=True, expire=60)
    def builders(self, branch):
        """Return a list of valid builders for this branch"""
        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        retval = get_builders(branch)

        return self._format(retval)

    @beaker_cache(query_args=True, expire=60)
    def builder(self, branch, builder_name):
        """Return a list of builds running for this builder"""
        abort(501, "Unimplemented")

    @beaker_cache(query_args=True, expire=60)
    def user(self, branch, user):
        """Return a list of builds for this user"""
        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)
        else:
            builds = getBuildsForUser(branch, user, limit=200)
            return self._ok(builds)

    def job_status(self, job_id):
        """Return information about a job request"""
        s = Session()
        r = s.query(JobRequest).get(job_id)

        if not r:
            return self._failed("Job %s not found" % job_id, 404)

        retval = r.asDict()

        return self._ok(retval)

    def reprioritize(self, branch, request_id):
        """
        Reprioritize the given request.

        Requires `priority` in the POST parameters.

        Higher priority values get handled first, and the default priority for
        jobs is 0.

        Returns a job status message."""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        try:
            priority = IntValidator.to_python(request.POST.get('priority'))
        except formencode.Invalid:
            return self._failed('Bad priority', 400)

        try:
            request_id = IntValidator.to_python(request_id)
        except ValueError:
            return self._failed('Non-integer request id', 400)

        retval = getRequest(branch, request_id)
        if not retval:
            return self._failed("Request %s not found on branch %s" %
                    (request_id, branch), 404)

        if retval['complete'] != 0:
            return self._failed("Request already complete", 400)
        elif retval['claimed_at'] != 0:
            return self._failed("Request is already running", 400)
        else:
            access_log.info("%s reprioritize %s %s to %s", who, branch,
                    request_id, priority)
            return self._format_mq_response(g.mq.reprioritizeRequest(who,
                request_id, priority))

        # TODO: invalidate cache for branch
        return self._format(retval)

    def cancel_request(self, branch, request_id):
        """Cancel the given request"""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        try:
            request_id = int(request_id)
        except ValueError:
            return self._failed('Non-integer request_id', 400)

        retval = getRequest(branch, request_id)
        if not retval:
            return self._failed("Request %s not found on branch %s" %
                    (request_id, branch), 404)

        # TODO: invalidate cache for branch
        access_log.info("%s cancel_request %s %s", who, branch, request_id)
        return self._format_mq_response(g.mq.cancelRequest(who, request_id))

    def cancel_build(self, branch, build_id):
        """Cancel the given build"""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        try:
            build_id = int(build_id)
        except ValueError:
            return self._failed('Non-integer build_id', 400)

        retval = getBuild(branch, build_id)
        if not retval:
            return self._failed("Build %s not found on branch %s" %
                    (build_id, branch), 404)

        access_log.info("%s cancel_build %s %s", who, branch, build_id)
        retval = g.mq.cancelBuild(who, build_id)
        # TODO: invalidate cache for branch
        return self._format_mq_response(retval)

    def rebuild_build(self, branch):
        """Rebuild `build_id`, which must be passed in as a POST parameter.

        `priority` is also accepted as an optional parameter."""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        try:
            build_id = IntValidator.to_python(request.POST.get('build_id'))
        except formencode.Invalid:
            return self._failed('Bad build_id', 400)

        try:
            priority = validators.Int(if_empty=0).to_python(request.POST.get('priority'))
        except formencode.Invalid:
            return self._failed('Bad priority', 400)

        retval = getBuild(branch, build_id)
        if not retval:
            return self._failed("Build %s not found on branch %s" % (build_id, branch), 404)

        access_log.info("%s rebuild_build %s %s %s", who, branch, build_id, priority)
        retval = g.mq.rebuildBuild(who, build_id, priority)
        # TODO: invalidate cache for branch
        return self._format_mq_response(retval)

    def rebuild_request(self, branch):
        """
        Rebuild  `request_id`, which must be passed in as a POST parameter.

        `priority` is also accepted as an optional parameter."""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        try:
            request_id = IntValidator.to_python(request.POST.get('request_id'))
        except:
            return self._failed('Bad request_id', 400)

        try:
            priority = validators.Int(if_empty=0).to_python(request.POST.get('priority'))
        except formencode.Invalid:
            return self._failed('Bad priority', 400)

        retval = getRequest(branch, request_id)
        if not retval:
            return self._failed("Request %s not found on branch %s" % (request_id, branch), 404)

        access_log.info("%s rebuild_request %s %s %s", who, branch, request_id, priority)
        retval = g.mq.rebuildRequest(who, request_id, priority)
        # TODO: invalidate cache for branch
        return self._format_mq_response(retval)

    def cancel_revision(self, branch, revision):
        """Cancels all running or pending builds on this revision"""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        # Force short form of revision
        revision = revision[:12]

        access_log.info("%s cancel_revision %s %s", who, branch, revision)
        retval = g.mq.cancelRevision(who, branch, revision)
        # TODO: invalidate cache for branch
        return self._format_mq_response(retval)

    def new_build_at_rev(self, branch, revision):
        """Creates a new build at this revision"""
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        access_log.info("%s new_build of %s %s", who, branch, revision)
        retval = g.mq.newBuildAtRevision(who, branch, revision)
        response.status = 202
        # TODO: invalidate cache for branch
        return self._format(retval)

    def new_build_for_builder(self, branch, builder_name):
        who = self._require_auth()

        if branch not in config['branches']:
            return self._failed("Branch %s not found" % branch, 404)

        # TODO: Make sure that the 'fake' branches for sourcestamps are obeyed?
        abort(501, "Unimplemented")

