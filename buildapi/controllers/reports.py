import formencode
import urllib

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify
from pylons.decorators.cache import beaker_cache

from buildapi.controllers.validators import PushesSchema, WaittimesSchema, \
EndtoendSchema, EndtoendRevisionSchema, BuildersSchema, BuilderDetailsSchema
from buildapi.lib import helpers as h
from buildapi.lib.base import BaseController, render
from buildapi.lib.visualization import gviz_pushes, gviz_waittimes, \
gviz_builders, gviz_trychooser_authors, gviz_trychooser_runs, gviz_testruns, gviz_idlejobs
from buildapi.model.builders import GetBuildersReport, GetBuilderTypeReport
from buildapi.model.endtoend import GetEndtoEndTimes, GetBuildRun
from buildapi.model.pushes import GetPushes
from buildapi.model.trychooser import TryChooserGetEndtoEndTimes
from buildapi.model.waittimes import GetWaitTimes, BUILDPOOL_MASTERS, get_time_interval
from buildapi.model.testruns import GetTestRuns, ALL_BRANCHES

class ReportsController(BaseController):

    @beaker_cache(query_args=True)
    def idlejobs(self):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)
        params = self._get_report_params()
        c.idlejobs = GetIdleJobsReport(**params)

        if format == 'json':
            return c.idlejobs.jsonify()
        elif format == 'chart':
            return gviz_idlejobs(c.idlejobs)
        else:
            return render('/reports/idlejobs.mako')

   @beaker_cache(query_args=True)
    def testruns(self):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        category = request.GET.getone('category') if 'category' in request.GET else None
        platform = request.GET.getone('platform') if 'platform' in request.GET else None
        group = request.GET.getone('group') if 'group' in request.GET else None
        btype = request.GET.getone('btype') if 'btype' in request.GET else None

        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)
        params = self._get_report_params()
        params['category'] = category
        params['platform'] = platform
        params['group'] = group
        params['btype'] = btype
        c.testruns = GetTestRuns(**params)

        if format == 'json':
            return c.testruns.jsonify()
        elif format == 'chart':
            return gviz_testruns(c.testruns)
        else:
            return render('/reports/testruns.mako')

    def builders(self, branch_name='mozilla-central'):
        """Average Time per Builder Report Controller."""
        req_params = dict(request.params)
        req_params.update(branch_name=branch_name)
        params = self._validate(BuildersSchema(), req_params)

        format = params['format']
        if format == 'html':
            # if html, fetch all results by ignoring all filters
            # (by ignoring the fiter parameters, the defaults will be used)
            report_params = dict([(k, params[k]) for k in 
                    ('starttime', 'endtime', 'branch_name')])
        else:
            report_params = dict([(k, params[k]) for k in 
                    ('starttime', 'endtime', 'branch_name',
                    'platform', 'build_type', 'job_type', 'detail_level')])

        @beaker_cache(expire=600, cache_response=False)
        def builders_getReport(**params):
            return GetBuildersReport(**params)
        c.report = builders_getReport(**report_params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            return gviz_builders(c.report, req_id=req_id)
        else:
            return render('/reports/builders.mako')

    def builder_details(self, buildername=None):
        """Builder Report Controller."""
        req_params = dict(request.params)
        req_params.update(buildername=urllib.unquote_plus(buildername))
        params = self._validate(BuilderDetailsSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
                ('starttime', 'endtime', 'buildername')])

        @beaker_cache(expire=600, cache_response=False)
        def builder_details_geReport(**params):
            return GetBuilderTypeReport(**params)
        c.report = builder_details_geReport(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            return render('/reports/builder_details.mako')

    def endtoend(self, branch_name='mozilla-central'):
        """End to End Times Report Controller."""
        req_params = dict(request.params)
        req_params.update(branch_name=branch_name)
        params = self._validate(EndtoendSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
                ('starttime', 'endtime', 'branch_name')])

        @beaker_cache(expire=600, cache_response=False)
        def endtoend_getReport(**params):
            return GetEndtoEndTimes(**params)
        c.report = endtoend_getReport(**report_params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            return gviz_endtoend(c.report, req_id=req_id)
        else:
            return render('/reports/endtoend.mako')

    def endtoend_revision(self, branch_name='mozilla-central', revision=None):
        """Revision Report Controller."""
        req_params = dict(request.params)
        req_params.update(branch_name=branch_name, revision=revision)
        params = self._validate(EndtoendRevisionSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in ('branch_name', 'revision')])

        @beaker_cache(expire=600, cache_response=False)
        def endtoend_revision_getReport(**params):
            return GetBuildRun(**params)
        c.report = endtoend_revision_getReport(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            return render('/reports/buildrun.mako')

    def pushes(self):
        """Pushes Report Controller."""
        params = self._validate(PushesSchema(), request.params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
                ('starttime', 'endtime', 'int_size', 'branch')])

        @beaker_cache(expire=600, cache_response=False)
        def pushes_getReport(**params):
            return GetPushes(**params)
        c.report = pushes_getReport(**report_params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            return gviz_pushes(c.report, req_id=req_id)
        else:
            return render('/reports/pushes.mako')

    def waittimes(self, pool='buildpool'):
        """Wait Times Report Controller."""
        req_params = dict(request.params)
        req_params.update(pool=pool)
        params = self._validate(WaittimesSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
                ('pool', 'mpb', 'starttime', 'endtime', 'int_size', 'maxb')])

        @beaker_cache(expire=600, cache_response=False)
        def waittimes_getReport(**params):
            return GetWaitTimes(**params)
        c.report = waittimes_getReport(**report_params)

        num = params['num']
        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            return gviz_waittimes(c.report, num=num, req_id=req_id)
        else:
            c.jscode_data = gviz_waittimes(c.report, num, resp_type='JSCode')
            return render('/reports/waittimes.mako')

    def trychooser(self, branch_name='mozilla-central'):
        """TryChooser Report Controller."""
        req_params = dict(request.params)
        req_params.update(branch_name=branch_name)
        params = self._validate(EndtoendSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
                ('starttime', 'endtime', 'branch_name')])

        @beaker_cache(expire=600, cache_response=False)
        def trychooser_getReport(**params):
            return TryChooserGetEndtoEndTimes(**params)
        c.report = trychooser_getReport(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            c.jscode_data_authors = gviz_trychooser_authors(c.report, resp_type='JSCode')
            c.jscode_data_runs = gviz_trychooser_runs(c.report, resp_type='JSCode')
            return render('/reports/trychooser.mako')

    def _validate(self, schema, params, status=None):
        """Validate parameters against the specified schema and return a 400 HTTP error 
        if the parameters are invalid.
        """
        try:
            return schema.to_python(params, status)
        except formencode.Invalid, e:
            abort(400, e)
