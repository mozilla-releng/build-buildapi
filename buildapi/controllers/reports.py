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
from buildapi.model.endtoend import GetEndtoEndTimes, GetBuildRun
from buildapi.lib.visualization import gviz_waittimes

class ReportsController(BaseController):
    def pushes(self):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)

        params = self._get_report_params()

        @beaker_cache(expire=600, cache_response=False)
        def getReport(**params):
            return GetPushes(**params)
        c.report = getReport(**params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            return gviz_pushes(c.report)
        else:
            return render('/reports/pushes.mako')

    def waittimes(self, pool='buildpool'):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)

        if pool not in BUILDPOOL_MASTERS:
            abort(400, detail='Unknown build pool name: %s. Try one of the following: %s.' %
                    (pool, ', '.join(BUILDPOOL_MASTERS.keys())))

        num = request.GET.getone('num') if 'num' in request.GET else 'full'
        if num not in ('full', 'ptg'):
            abort(400, detail='Unknown wait times number format: %s. Try one of the following: ptg, full.' % num)

        params = self._get_report_params()
        params['pool'] = pool
        try:
            if 'mpb' in request.GET:
                params['minutes_per_block'] = int(request.GET.getone('mpb'))
            if 'maxb' in request.GET:
                params['maxb'] = int(request.GET.getone('maxb'))
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)

        @beaker_cache(expire=600, cache_response=False)
        def getReport(**params):
            return GetWaitTimes(**params)
        c.report = getReport(**params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            return gviz_waittimes(c.report, num)
        else:
            c.jscode_data = gviz_waittimes(c.report, num, resp_type='JSCode')
            return render('/reports/waittimes.mako')

    def endtoend(self, branch='mozilla-central'):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)

        params = self._get_report_params()
        params['branch'] = branch
        del params['int_size']

        @beaker_cache(expire=600, cache_response=False)
        def getReport(**params):
            return GetEndtoEndTimes(**params)
        c.report = getReport(**params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            return gviz_endtoend(c.report)
        else:
            return render('/reports/endtoend.mako')

    def endtoend_revision(self, revision=None):
        @beaker_cache(expire=600, cache_response=False)
        def getReport(**params):
            return GetBuildRun(**params)
        c.report = getReport(revision=revision)

        return render('/reports/buildrun.mako')

    def _get_report_params(self):
        params = {}
        try: 
            if 'starttime' in request.GET:
                params['starttime'] = float(request.GET.getone('starttime'))
            if 'endtime' in request.GET:
                params['endtime'] = float(request.GET.getone('endtime'))
            if 'int' in request.GET:
                params['int_size'] = int(request.GET.getone('int'))
            else:
                params['int_size'] = 3600*2
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)
        
        if params['int_size'] < 0:
            abort(400, detail='Time interval (int parameter) must be higher than 0: %s.' % params['int_size'])
        
        return params
