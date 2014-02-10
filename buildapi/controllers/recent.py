import logging
import datetime

from pylons import request, tmpl_context as c, app_globals as g
from pylons.controllers.util import abort

from buildapi.lib.base import BaseController, render
from buildapi.model.query import GetHistoricBuilds
from buildapi.lib import times

log = logging.getLogger(__name__)

class RecentController(BaseController):

    def index(self, slave=None):
        if 'numbuilds' in request.GET:
            count = int(request.GET.getone('numbuilds'))
        else:
            count = 25

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
            for b in builds:
                for k,v in b.items():
                    if isinstance(v, datetime.datetime):
                        v = times.UTC.localize(v)
                        b[k] = times.dt2ts(v)
            return self.jsonify(builds)
