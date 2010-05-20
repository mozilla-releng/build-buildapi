import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify

from buildapi.lib.base import BaseController, render
import buildapi.model.meta as meta

log = logging.getLogger(__name__)

class PendingController(BaseController):
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

        if branch is None:
            # Look for pending builds in all branches
            c.pending_builds = [{"id": 1}, {"id": 2}]
            meta.scheduler_db_meta.tables['buildrequests'].select().execute()
        else:
            # Look for pending builds in the specified branches
            c.pending_builds = [{"id": 2}]

        # Return a rendered template
        #return render('/pending.mako')
        # or, return a string
        if format == "html":
            return render("/pending.mako")
        else:
            return self.jsonify({'pending': c.pending_builds})
