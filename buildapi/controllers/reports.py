import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify
from pylons.decorators.cache import beaker_cache

from buildapi.lib import helpers as h
from buildapi.lib.base import BaseController, render
from buildapi.lib.visualization import gviz_pushes
from buildapi.model.pushes import GetPushes
from buildapi.model.waittimes import GetWaitTimes, BUILDPOOL_MASTERS

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

    @beaker_cache(query_args=True)
    def waittimes(self, pool='buildpool'):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json'):
            abort(400, detail='Unsupported format: %s' % format)

        if pool not in BUILDPOOL_MASTERS:
            abort(400,
                  detail='Unknown build pool name: %s. Try one of the following: %s.' %
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
            if 'maxb' in request.GET:
                params['maxb'] = int(request.GET.getone('maxb'))
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)

        c.wait_times = GetWaitTimes(**params)

        if format == 'json':
            return c.wait_times.jsonify()
        else:
            return render('/waittimes.mako')
