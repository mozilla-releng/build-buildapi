import simplejson
from sqlalchemy import or_

import buildapi.model.meta as meta
from buildapi.model.buildrequest import BuildRequest, BuildRequestsQuery
from buildapi.model.util import BUILDSET_REASON, PENDING, RUNNING, COMPLETE, \
CANCELLED, INTERRUPTED, MISC
from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, \
SKIPPED, EXCEPTION, RETRY
from buildapi.model.util import get_time_interval, get_branch_name, \
get_platform, get_build_type, get_job_type, get_revision, results_to_str

br = meta.scheduler_db_meta.tables['buildrequests']
s = meta.scheduler_db_meta.tables['sourcestamps']
c = meta.scheduler_db_meta.tables['changes']

def BuildRunQuery(revision, branch_name=None):
    """Constructs the sqlalchemy query for fetching all build requests in a 
    build run (sharing the same sourcestamps.revision number).

    Input: revision - sourcestamps.revision (first 12 chars are enough), or 
                None for nigthtlies
           branch_name - branch name; if not specified, no restriction is 
                applied on branch
    Output: query
    """
    q = BuildRequestsQuery()

    if not revision:
        q = q.where(s.c.revision==None)
    else:
        q = q.where(s.c.revision.like(revision + '%'))
    if branch_name:
        q = q.where(s.c.branch.like('%' + branch_name + '%'))

    return q

def EndtoEndTimesQuery(starttime, endtime, branch_name):
    """Constructs the sqlalchemy query for fetching all build requests in the 
    specified time interval for the specified branch.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branch_name - branch name
    Output: query
    """
    q = BuildRequestsQuery()

    q = q.where(s.c.branch.like('%' + branch_name + '%'))
    # ??? first build job in push started, not all! --> what condition on rest??
    q = q.where(or_(c.c.when_timestamp >= starttime, br.c.submitted_at >= starttime))
    q = q.where(or_(c.c.when_timestamp < endtime, br.c.submitted_at < endtime))

    return q

def GetEndtoEndTimes(starttime=None, endtime=None, branch_name='mozilla-central'):
    """Get end to end times report for the speficied time interval and branch.

    Input: starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
           branch_name - branch name, default vaue is 'mozilla-central'
    Output: EndtoEndTimesReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = EndtoEndTimesQuery(starttime, endtime, branch_name)
    q_results = q.execute()

    report = EndtoEndTimesReport(starttime, endtime, branch_name)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        br = BuildRequest(**params)
        report.add_build_request(br)

    return report

def GetBuildRun(branch_name=None, revision=None):
    """Get build run report. The build run report is specified by its 
    sourcestamps.revision number.

    Input: revision - sourcestamps.revision (first 12 chars are enough), or 
                None for nigthtlies
    Output: BuildRun
    """
    q_results = BuildRunQuery(revision, branch_name=branch_name).execute()

    report = BuildRun(revision, branch_name)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        br = BuildRequest(**params)
        report.add(br)

    return report

class EndtoEndTimesReport(object):
    outdated = -1

    def __init__(self, starttime, endtime, branch_name):
        self.starttime = starttime
        self.endtime = endtime
        self.branch_name = branch_name

        self._init_report() 

    def _init_report(self):
        self._runs = {}
        self._total_br = 0
        self._u_total_br = 0
        self._avg_run_duration = 0

    def get_total_build_runs(self):
        return len(self._runs)

    def get_total_build_requests(self):
        if self._total_br == EndtoEndTimesReport.outdated:
            self._total_br = sum([self._runs[r].get_total_build_requests() for r in self._runs])

        return self._total_br

    def get_unique_total_build_requests(self):
        if self._u_total_br == EndtoEndTimesReport.outdated:
            self._u_total_br = \
                sum([self._runs[r].get_unique_total_build_requests() for r in self._runs])

        return self._u_total_br

    def get_avg_duration(self):
        if self._avg_run_duration == EndtoEndTimesReport.outdated:
            if self.get_total_build_runs():
                self._avg_run_duration = sum([self._runs[r].get_duration() for r in self._runs]) / self.get_total_build_runs()
            else:
                self._avg_run_duration = 0

        return self._avg_run_duration

    def add_build_request(self, br):
        if br.revision not in self._runs: 
            self._runs[br.revision] = BuildRun(br.revision, br.branch_name)
        self._runs[br.revision].add(br)

        self._total_br = EndtoEndTimesReport.outdated
        self._u_total_br = EndtoEndTimesReport.outdated
        self._avg_run_duration = EndtoEndTimesReport.outdated

    def to_dict(self, summary=False):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'branch_name': self.branch_name,
            'total_build_requests': self.get_total_build_requests(),
            'unique_total_build_requests': self.get_unique_total_build_requests(),
            'total_build_runs': self.get_total_build_runs(),
            'avg_duration': self.get_avg_duration(),
            'build_runs': {},
        }
        if not summary:
            for brun_key in self._runs:
                json_obj['build_runs'][brun_key] = self._runs[brun_key].to_dict(summary=True)

        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))

class BuildRun(object):
    outdated = -1

    def __init__(self, revision, branch_name):
        self.revision = revision
        self.branch_name = branch_name

        self.build_requests = []

        self.lst_change_time = 0
        self.gst_finish_time = 0
        self.gst_complete_at_time = 0

        self._total_br = 0     # total build requests
        self._u_total_br = 0   # unique total build request ids

        self.complete = 0
        self.running = 0
        self.pending = 0
        self.cancelled = 0
        self.interrupted = 0
        self.misc = 0
        self.rebuilds = 0
        self.forcebuilds = 0

        self.unittests = []
        self.talos = []
        self.builds = []

        self.results_success = 0
        self.results_warnings = 0
        self.results_failure = 0
        self.results_other = 0
        self.results = NO_RESULT

    def add(self, br):
        self.build_requests.append(br)

        self._total_br += 1
        self._u_total_br = BuildRun.outdated  # needs recalculation
        if br.status == PENDING:
            self.pending += 1
        elif br.status == RUNNING:
            self.running += 1
        elif br.status == COMPLETE:
            self.complete += 1
        elif br.status == CANCELLED:
            self.cancelled += 1
        elif br.status == INTERRUPTED:
            self.interrupted += 1
        else:
            self.misc += 1

        if br.when_timestamp and (br.when_timestamp < self.lst_change_time or not self.lst_change_time):
            self.lst_change_time = br.when_timestamp
        if br.finish_time and (br.finish_time > self.gst_finish_time):
            self.gst_finish_time = br.finish_time
        if br.complete_at and (br.complete_at > self.gst_complete_at_time):
            self.gst_complete_at_time = br.complete_at

        if BUILDSET_REASON['rebuild'].match(br.reason):
            self.rebuilds += 1
        if BUILDSET_REASON['forcebuild'].match(br.reason):
            self.forcebuilds += 1

        if br.results == SUCCESS:
            self.results_success += 1
        elif br.results == WARNINGS:
            self.results_warnings += 1
        elif br.results in (FAILURE, SKIPPED, EXCEPTION, RETRY):
            self.results_failure += 1
        else:
            self.results_other += 1
        self.results = max(self.results, br.results)

        if br.when_timestamp:
            if br.branch.endswith('unittest'):
                self.unittests.append(br.when_timestamp)
            elif br.branch.endswith('talos'):
                self.talos.append(br.when_timestamp)
            else:
                self.builds.append(br.when_timestamp)

    def get_duration(self):
        return self.gst_complete_at_time - self.lst_change_time if self.gst_complete_at_time and self.lst_change_time else 0

    def get_total_build_requests(self):
        return self._total_br

    def get_unique_total_build_requests(self):
        if self._u_total_br == BuildRun.outdated:
            self._u_total_br = len(set([br.brid for br in self.build_requests]))

        return self._u_total_br

    def is_complete(self):
        return not(self.running or self.pending)

    def to_dict(self, summary=False):
        json_obj = {
            'revision': self.revision,
            'results': self.results,
            'results_str': results_to_str(self.results),
            'is_complete': 'yes' if self.is_complete() else 'no',
            'total_build_requests': self.get_total_build_requests(),
            'duration': self.get_duration(),
            'lst_change_time': self.lst_change_time,
            'gst_finish_time': self.gst_finish_time,
            'complete': self.complete,
            'running': self.running,
            'pending': self.pending,
            'cancelled': self.cancelled,
            'interrupted': self.interrupted,
            'misc': self.misc,
            'rebuilds': self.rebuilds,
            'forcebuilds': self.forcebuilds,
            'builds': len(self.builds),
            'unittests': len(self.unittests),
            'talos': len(self.talos),
        }
        if not summary:
            json_obj['build_requests'] = [br.to_dict() for br in self.build_requests]

        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))
