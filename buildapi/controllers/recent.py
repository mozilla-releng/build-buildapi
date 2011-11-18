import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify

from buildapi.lib.base import BaseController, render
from buildapi.model.query import GetHistoricBuilds

log = logging.getLogger(__name__)

class RecentController(BaseController):

    def index(self, slave=None, count=20):
        if 'count' in request.GET:
            count = int(request.GET.getone('count'))

        if 'format' in request.GET:
            format = request.GET.getone('format')
        else:
            format = 'html'
        if format not in ('html', 'json'):
            abort(400, detail='Unsupported format: %s' % format)

#        if slave is not None:
#            slave = slave[0]
        if 'slave' in request.GET:
            slave = request.GET.getall('slave')

        builds = GetHistoricBuilds(slave=slave, count=count)

        # Return a rendered template
        # or, return a json blob
        if format == "html":
            c.recent_builds = builds
            return render("/recent.mako")
        else:
            return self.jsonify(builds)
