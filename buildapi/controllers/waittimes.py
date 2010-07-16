import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify

from buildapi.lib import helpers as h
from buildapi.lib.base import BaseController, render
from buildapi.model.query import GetWaitTimes, BUILDPOOL_MASTERS

log = logging.getLogger(__name__)

class WaittimesController(BaseController):

    def __init__(self, **kwargs):
        BaseController.__init__(self, **kwargs)

    def index(self, pool='buildpool'):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json'):
            abort(400, detail='Unsupported format: %s' % format)
        
        if pool not in BUILDPOOL_MASTERS:
            abort(400, detail='Unknown build pool name: %s. Try one of the following: %s.' % 
                (pool, ', '.join(BUILDPOOL_MASTERS.keys())))

        params = {}
        params['pool'] = pool
        try: 
            if 'starttime' in request.GET:
                params['starttime'] = float(request.GET.getone('starttime'))
            if 'endtime' in request.GET:
                params['endtime'] = float(request.GET.getone('endtime'))
            if 'mpb' in request.GET:
                params['minutes_per_block'] = int(request.GET.getone('mpb'))
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)
        
        c.wait_times = GetWaitTimes(**params)

        # Return a rendered template
        # or, return a json blob
        if format == 'html':
            return render('/waittimes.mako')
        else:
            results = {'waittimes': c.wait_times}
            return self.jsonify(results)
	