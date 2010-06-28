import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify

from datetime import date

from buildapi.lib.base import BaseController, render
from buildapi.model.query import GetPushes, GetAllBranches

log = logging.getLogger(__name__)

class PushesController(BaseController):

    def index(self, branch=None, fromtime=None, totime=None):
        # First non-mobile change in the db is "Thu May 27 08:09:58 2010 PDT"
        db_start = 1274972998
        # First mobile change in the db is "Thu Jun 24 15:13:19 2010 PDT"
        db_start_mobile = 1277417599

        if 'format' in request.GET:
            format = request.GET.getone('format')
        else:
            format = 'html'
        if format not in ('html', 'json'):
            abort(400, detail='Unsupported format: %s' % format)

        if not fromtime and 'fromtime' in request.GET:
            fromtime = request.GET.getone('fromtime')
        # magic string
        if fromtime == 'today':
            fromtime = date.today().strftime('%s')
        # sanitize a little
        if fromtime:
            fromtime = int(fromtime);
        # don't mislead over the amount of history we have
        if branch.startswith('mobile') and fromtime < db_start_mobile:
            fromtime = db_start_mobile
        elif fromtime < db_start:
            fromtime = db_start

        if totime:
            totime = int(totime)
        elif 'totime' in request.GET:
            totime = int(request.GET.getone('totime'))

        c.pushes = GetPushes(branch, fromtime, totime)
        c.push_limits = {'branch': branch, 'fromtime': fromtime, 'totime': totime}

        # Return a rendered template
        # or, return a json blob
        if format == "html":
            return render("/pushes.mako")
        else:
            return self.jsonify(c.pushes)

