
import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify

from buildapi.lib.base import BaseController, render
from buildapi.model.query import GetBuilds

log = logging.getLogger(__name__)

class ResultsController(BaseController):

    def __init__(self, pending=True, running=False, complete=False,
                 revision=False,
                 template=None, **kwargs):
        BaseController.__init__(self, **kwargs)
        self.pending  = pending
        self.running  = running
        self.complete = complete
        self.revision = revision
        self.template = template

    def index(self, branch=None, platform=None, rev=None):
        if 'format' in request.GET:
            format = request.GET.getone('format')
        else:
            format = 'html'
        if format not in ('html', 'json'):
            abort(400, detail='Unsupported format: %s' % format)

        if branch is not None:
            branch = [branch]
        elif 'branch' in request.GET:
            branch = request.GET.getall('branch')

        if rev is not None:
            rev = [rev]
        elif 'rev' in request.GET:
            rev = request.GET.getone('rev')

        if self.pending:
            c.pending_builds = GetBuilds(branch=branch, type='pending')
        if self.running:
            c.running_builds = GetBuilds(branch=branch, type='running')
        if self.revision:
            c.all_builds = GetBuilds(branch=branch, type='revision', rev=rev)
            c.branch = branch[0]
            c.revision = rev[0]

        # Return a rendered template
        # or, return a json blob
        if format == "html":
            if self.template:
                return render(self.template)
        else:
            results = {}
            if self.pending:
              results['pending'] = c.pending_builds
            if self.running:
              results['running'] = c.running_builds
            if self.revision:
              results['all'] = c.all_builds
              results['branch'] = branch[0]
              results['revision'] = rev[0]
            return self.jsonify(results)
