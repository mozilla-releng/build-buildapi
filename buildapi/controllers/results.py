import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify

from buildapi.lib.base import BaseController, render
from buildapi.model.query import GetBuilds

log = logging.getLogger(__name__)

class ResultsController(BaseController):

    def __init__(self, pending=True, running=False, complete=False,
                 template=None, **kwargs):
        BaseController.__init__(self, **kwargs)
        self.pending  = pending
        self.running  = running
        self.complete = complete
        self.template = template

    def index(self, branch=None, platform=None):
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

        if self.pending:
            c.pending_builds = GetBuilds(branch=branch, type='pending')
        if self.running:
            c.running_builds = GetBuilds(branch=branch, type='running')

        # Return a rendered template
        # or, return a json blob
        if format == "html":
            if self.template:
                return render(self.template)
        else:
            return self.jsonify({'pending': c.pending_builds})
