import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify
from pylons.decorators.cache import beaker_cache

from buildapi.lib import helpers as h
from buildapi.lib.base import BaseController, render
from buildapi.lib.visualization import gviz_pushes
from buildapi.model.pushes import GetPushes
from buildapi.model.waittimes import GetWaitTimes, BUILDPOOL_MASTERS, get_time_interval
from buildapi.lib.visualization import gviz_waittimes

class ReportsController(BaseController):
    @beaker_cache(query_args=True)
    def sourcestamps(self):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)

        params = {}
        try:
            if 'starttime' in request.GET:
                params['starttime'] = float(request.GET.getone('starttime'))
            if 'endtime' in request.GET:
                params['endtime'] = float(request.GET.getone('endtime'))
            if 'int' in request.GET:
                params['int_size'] = int(request.GET.getone('int'))
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)

        if 'int_size' not in params or params['int_size']<=0:
            abort(400, detail='Time interval (int parameter) must be higher than 0: %s.' % int_size)

        c.report = GetPushes(**params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            return gviz_pushes(c.report)
        else:
            return render('/sourcestamps.mako')

    #@beaker_cache(query_args=True)
    def waittimes(self, pool='buildpool'):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)

        if pool not in BUILDPOOL_MASTERS:
            abort(400,
                  detail='Unknown build pool name: %s. Try one of the following: %s.' %
                    (pool, ', '.join(BUILDPOOL_MASTERS.keys())))

        num = request.GET.getone('num') if 'num' in request.GET else 'full'
        if num not in ('full', 'ptg'):
            abort(400, detail='Unknown wait times number format: %s. Try one of the following: ptg, full.' % num)

        params = {}
        params['pool'] = pool
        try:
            if 'starttime' in request.GET:
                params['starttime'] = float(request.GET.getone('starttime'))
            if 'endtime' in request.GET:
                params['endtime'] = float(request.GET.getone('endtime'))
            if 'mpb' in request.GET:
                params['minutes_per_block'] = int(request.GET.getone('mpb'))
            if 'int' in request.GET:
                params['int_size'] = int(request.GET.getone('int'))
            if 'maxb' in request.GET:
                params['maxb'] = int(request.GET.getone('maxb'))
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)

        int_size = params['int_size'] if 'int_size' in params else 3600*6
        if not int_size:
            abort(400, detail='Time interval (int parameter) must be higher than 0: %s.' % int_size)

        @beaker_cache(expire=600, cache_response=False)
        def getReport(**params):
            return GetWaitTimes(**params)
        c.wait_times = getReport(**params)

        starttime = params['starttime'] if 'starttime' in params else None
        endtime = params['endtime'] if 'endtime' in params else None
        c.starttime, c.endtime = get_time_interval(starttime, endtime)

        if format == 'json':
            return c.wait_times.jsonify()
        elif format == 'chart':
            return gviz_waittimes(c.wait_times, num)
        else:
            c.jscode_data = gviz_waittimes(c.wait_times, num, resp_type='JSCode')
            return render('/waittimes.mako')
