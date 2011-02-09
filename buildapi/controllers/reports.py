import formencode
import urllib

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators.cache import beaker_cache

from buildapi.controllers.validators import PushesSchema, WaittimesSchema, \
EndtoendSchema, EndtoendRevisionSchema, BuildersSchema, BuilderDetailsSchema, \
IdleJobsSchema, SlaveDetailsSchema, SlavesSchema, TestRunSchema, \
StatusBuildersSchema, StatusBuilderDetailsSchema
from buildapi.lib import helpers as h
from buildapi.lib.base import BaseController, render
from buildapi.lib.visualization import gviz_pushes, gviz_pushes_intervals, \
gviz_pushes_daily_intervals, gviz_waittimes, gviz_builders, \
gviz_slaves, gviz_slaves_busy, gviz_slaves_int_busy, \
gviz_trychooser_authors, gviz_trychooser_runs, gviz_testruns, gviz_idlejobs, \
csv_slaves_int_busy_silos, gviz_waittimes
from buildapi.model.builders import GetBuildersReport, GetBuilderTypeReport
from buildapi.model.endtoend import GetEndtoEndTimes, GetBuildRun
from buildapi.model.idlejobs import GetIdleJobsReport
from buildapi.model.pushes import GetPushes
from buildapi.model.slaves import GetSlaveDetailsReport, \
GetSlavesReport, GetBuilderDetailsReport, GetStatusBuildersReport
from buildapi.model.testruns import GetTestRuns
from buildapi.model.trychooser import TryChooserGetEndtoEndTimes
from buildapi.model.testruns import GetTestRuns
from buildapi.model.waittimes import GetWaitTimes

import logging
log = logging.getLogger(__name__)

class ReportsController(BaseController):

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
        def builders_get_report(**params):
            return GetBuildersReport(**params)
        c.report = builders_get_report(**report_params)

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
        def builder_details_get_report(**params):
            return GetBuilderTypeReport(**params)
        c.report = builder_details_get_report(**report_params)

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
        def endtoend_get_report(**params):
            return GetEndtoEndTimes(**params)
        c.report = endtoend_get_report(**report_params)

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
        report_params = dict([(k, params[k]) for k in 
            ('branch_name', 'revision')])

        @beaker_cache(expire=600, cache_response=False)
        def endtoend_revision_get_report(**params):
            return GetBuildRun(**params)
        c.report = endtoend_revision_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            return render('/reports/buildrun.mako')

    @beaker_cache(query_args=True)
    def idlejobs(self):
        """Idle Jobs Report Controller."""
        req_params = dict(request.params)
        params = self._validate(IdleJobsSchema(), req_params)
        format = params['format']
        report_params = dict([(v, params[v]) for v in 
            ('starttime', 'endtime', 'int_size')])
        c.idlejobs = GetIdleJobsReport(**report_params)

        if format == 'json':
            return c.idlejobs.jsonify()
        elif format == 'chart':
            return gviz_idlejobs(c.idlejobs)
        else:
            return render('/reports/idlejobs.mako')

    def revision(self):
        """Revision Report Homepage."""
        return render('/reports/buildrun_home.mako')

    def pushes(self):
        """Pushes Report Controller."""
        params = self._validate(PushesSchema(), request.params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('starttime', 'endtime', 'int_size', 'branches')])

        @beaker_cache(expire=600, cache_response=False)
        def pushes_get_report(**params):
            return GetPushes(**params)
        c.report = pushes_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            rtype = params['type']
            if rtype == 'int':
                return gviz_pushes_intervals(c.report, req_id=req_id)
            if rtype == 'hourly':
                return gviz_pushes_daily_intervals(c.report, req_id=req_id)
            else:
                return gviz_pushes(c.report, req_id=req_id)
        else:
            return render('/reports/pushes.mako')

    def slaves(self):
        """Slaves Report Controller."""
        params = self._validate(SlavesSchema(), request.params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('starttime', 'endtime', 'int_size', 'last_int_size')])

        @beaker_cache(expire=600, cache_response=False)
        def slaves_get_report(**params):
            return GetSlavesReport(**params)
        c.report = slaves_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            r_type = params['type']
            if r_type == 'silos':
                return csv_slaves_int_busy_silos(c.report)
            else:
                return gviz_slaves_int_busy(c.report, req_id=req_id)
        else:
            return render('/reports/slaves.mako')

    def slave_details(self, slave_id=None):
        """Slave Details Report Controller."""
        req_params = dict(request.params)
        req_params.update(slave_id=slave_id)
        params = self._validate(SlaveDetailsSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('slave_id', 'starttime', 'endtime', 'int_size', 'last_int_size')])

        @beaker_cache(expire=600, cache_response=False)
        def slave_details_get_report(**params):
            return GetSlaveDetailsReport(**params)
        c.report = slave_details_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            r_type = params['type']
            if r_type == 'busy':
                return gviz_slaves_busy(c.report, req_id=req_id)
            else:
                return gviz_slaves(c.report, req_id=req_id)
        else:
            return render('/reports/slave_details.mako')

    def status_builders(self):
        """Builders Report (based on statusdb) Controller."""
        params = self._validate(StatusBuildersSchema(), request.params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('starttime', 'endtime')])

        @beaker_cache(expire=600, cache_response=False)
        def status_builders_get_report(**params):
            return GetStatusBuildersReport(**params)
        c.report = status_builders_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            return render('/reports/status_builders.mako')

    def status_builder_details(self, builder_name=None):
        """Builder Details Report (based on statusdb) Controller."""
        req_params = dict(request.params)
        req_params.update(builder_name=urllib.unquote_plus(builder_name))
        params = self._validate(StatusBuilderDetailsSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('builder_name', 'starttime', 'endtime')])

        @beaker_cache(expire=600, cache_response=False)
        def status_builder_details_get_report(**params):
            return GetBuilderDetailsReport(**params)
        c.report = status_builder_details_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            return render('/reports/status_builder_details.mako')

    def waittimes(self, pool='buildpool'):
        """Wait Times Report Controller."""
        req_params = dict(request.params)
        req_params.update(pool=pool)
        params = self._validate(WaittimesSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('pool', 'mpb', 'starttime', 'endtime', 'int_size', 'maxb')])

        def waittimes_get_report(**params):
            return GetWaitTimes(**params)
        c.report = waittimes_get_report(**report_params)

        num = params['num']
        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            req_id = params['reqid']
            return gviz_waittimes(c.report, num=num, req_id=req_id)
        else:
            c.jscode_data = gviz_waittimes(c.report, num, resp_type='JSCode')
            return render('/reports/waittimes.mako')

    @beaker_cache(query_args=True)
    def testruns(self):
        """Test Runs Controller."""
        req_params = dict(request.params)
        params = self._validate(TestRunSchema(), req_params)
        format = params['format']
        report_params = dict([(v, params[v]) for v in 
            ('starttime', 'endtime', 'category', 'platform', 'group', 'btype')])
        c.testruns = GetTestRuns(**report_params)

        if format == 'json':
            return c.testruns.jsonify()
        elif format == 'chart':
            return gviz_testruns(c.testruns)
        else:
            return render('/reports/testruns.mako')

    def trychooser(self, branch_name='mozilla-central'):
        """TryChooser Report Controller."""
        req_params = dict(request.params)
        req_params.update(branch_name=branch_name)
        params = self._validate(EndtoendSchema(), req_params)

        format = params['format']
        report_params = dict([(k, params[k]) for k in 
            ('starttime', 'endtime', 'branch_name')])

        @beaker_cache(expire=600, cache_response=False)
        def trychooser_get_report(**params):
            return TryChooserGetEndtoEndTimes(**params)
        c.report = trychooser_get_report(**report_params)

        if format == 'json':
            return c.report.jsonify()
        else:
            c.jscode_data_authors = gviz_trychooser_authors(c.report, 
                resp_type='JSCode')
            c.jscode_data_runs = gviz_trychooser_runs(c.report, 
                resp_type='JSCode')
            return render('/reports/trychooser.mako')

    def _validate(self, schema, params, status=None):
        """Validate parameters against the specified schema and return a 400 
        HTTP error if the parameters are invalid.
        """        
        try:
            return schema.to_python(params, status)
        except formencode.Invalid, e:
            abort(400, e)
