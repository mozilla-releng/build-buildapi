from sqlalchemy import *
import buildapi.model.meta as meta
from buildapi.model.util import get_time_interval
from buildapi.model.pushes import get_branch_name
from pylons.decorators.cache import beaker_cache

import re, simplejson

BUILDSET_REASON = {
    'forcebuild': re.compile("The web-page 'force build' button was pressed by .+"),
    'rebuild': re.compile("The web-page 'rebuild' button was pressed by .+"),
}

NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(-1, 6)
RESULTS_TO_STR = {
    NO_RESULT: '-',
    SUCCESS: 'success',
    WARNINGS: 'warnings',
    FAILURE: 'failure',
    SKIPPED: 'skipped',
    EXCEPTION: 'exception',
    RETRY:'retry',
}

b = meta.scheduler_db_meta.tables['builds']
br = meta.scheduler_db_meta.tables['buildrequests']
bs = meta.scheduler_db_meta.tables['buildsets']
s = meta.scheduler_db_meta.tables['sourcestamps']
sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
c = meta.scheduler_db_meta.tables['changes']

def BuildRequestsQuery():
    """Constructs the sqlalchemy query for fetching all build requests.
    
    Input: None
    Output: query
    """
    q = outerjoin(br, b, b.c.brid==br.c.id) \
            .join(bs, bs.c.id==br.c.buildsetid) \
            .join(s, s.c.id==bs.c.sourcestampid) \
            .outerjoin(sch, sch.c.sourcestampid==s.c.id) \
            .outerjoin(c, c.c.changeid==sch.c.changeid) \
            .select() \
            .with_only_columns([b.c.number, br.c.id.label('brid'), br.c.buildername, s.c.branch, s.c.id.label('ssid'), \
                c.c.when_timestamp, br.c.submitted_at, br.c.claimed_at, b.c.start_time, \
                br.c.complete_at, b.c.finish_time, br.c.claimed_by_name, \
                s.c.revision, br.c.complete, bs.c.reason, br.c.results, \
                c.c.author, c.c.comments, c.c.revlink, c.c.category, c.c.repository, c.c.project, \
                br.c.buildsetid])

    q = q.group_by(br.c.id, b.c.id)  # some build request might have multiple builds

    return q

def BuildRunQuery(revision, branch_name=None):
    """Constructs the sqlalchemy query for fetching all build requests in a build run (sharing 
    the same sourcestamps.revision number).
    
    Input: revision - sourcestamps.revision (first 12 chars are enough), or None for nigthtlies
           branch_name - branch name; if not specified, no restriction is applied on branch
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
    """Constructs the sqlalchemy query for fetching all build requests in the specified time 
    interval for the specified branch.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branch_name - branch name
    Output: query
    """
    q = BuildRequestsQuery()
    
    q = q.where(s.c.branch.like('%' + branch_name + '%'))
    # ??? first build job in push started, not all! --> what condition on rest??
    q = q.where(or_(c.c.when_timestamp>=starttime, br.c.submitted_at>=starttime))
    q = q.where(or_(c.c.when_timestamp<=endtime, br.c.submitted_at<=endtime))
    
    return q

def GetEndtoEndTimes(starttime=None, endtime=None, branch_name='mozilla-central'):
    """Get end to end times report for the speficied time interval and branch.
    
    Input: starttime - start time (UNIX timestamp in seconds), if not specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, starttime plus 24 hours or 
                     current time (if starttime is not specified either)
           branch_name - branch name, default vaue is 'mozilla-central'
    Output: EndtoEndTimesReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    
    q = EndtoEndTimesQuery(starttime, endtime, branch_name)
    q_results = q.execute()
    
    report = EndtoEndTimesReport(starttime, endtime, branch_name)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        params['revision'] = params['revision'][:12] if params['revision'] else params['revision']

        br = BuildRequest(**params)
        report.add_build_request(br)
    
    return report
   
def GetBuildRun(branch_name=None, revision=None):
    """Get build run report. The build run report is specified by its sourcestamps.revision number.

    Input: revision - sourcestamps.revision (first 12 chars are enough), or None for nigthtlies
    Output: BuildRun
    """
    q_results = BuildRunQuery(revision, branch_name=branch_name).execute()

    report = BuildRun(revision, branch_name)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        params['revision'] = params['revision'][:12] if params['revision'] else params['revision']

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
            self._u_total_br = sum([self._runs[r].get_unique_total_build_requests() for r in self._runs])

        return self._u_total_br

    def get_avg_duration(self):
        if self._avg_run_duration == EndtoEndTimesReport.outdated:
            self._avg_run_duration = sum([self._runs[r].get_duration() for r in self._runs]) / self.get_total_build_runs()

        return self._avg_run_duration
            	
    def add_build_request(self, br):
        if br.revision not in self._runs: self._runs[br.revision] = BuildRun(br.revision, br.branch_name)
        self._runs[br.revision].add(br)
        
        self._total_br = EndtoEndTimesReport.outdated
        self._u_total_br = EndtoEndTimesReport.outdated
        self._avg_run_duration = EndtoEndTimesReport.outdated

    def jsonify(self):
        return simplejson.dumps({})

class BuildRequest(object):
    st_pending = 0
    st_running = 1
    st_complete = 2
    st_cancelled = 3
    st_interrupted = 4
    st_misc = 5
    
    _st_to_str = {
        st_pending: 'PENDING',
        st_running: 'RUNNING',
        st_complete: 'COMPLETE',
        st_cancelled: 'CANCELLED',
        st_interrupted: 'INTERRUPTED',
        st_misc: 'MISC',
    }

    def __init__(self, number=None, brid=None, branch=None, buildername=None, revision=None, ssid=None, \
        when_timestamp=None, submitted_at=None, claimed_at=None, start_time=None, complete_at=None, finish_time=None, \
        claimed_by_name=None, complete=0, reason=None, results=None, \
        author=None, comments=None, revlink=None, category=None, repository=None, project=None, \
        buildsetid=None):
        self.number = number
        self.brid = brid
        self.branch = branch
        self.branch_name = get_branch_name(branch)
        self.buildername = buildername
        self.ssid = ssid
        self.revision = revision    # sourcestamp revision number

        self.when_timestamp = when_timestamp
        self.submitted_at = submitted_at
        self.claimed_at = claimed_at
        self.start_time = start_time
        self.complete_at = complete_at
        self.finish_time = finish_time

        self.claimed_by_name = claimed_by_name
        self.complete = complete
        self.reason = reason
        self.results = results if results!=None else NO_RESULT

        self.status = self._compute_status()
        
        self.author = author
        self.comments = comments
        self.revlink = revlink
        self.category = category
        self.repository = repository 
        self.project = project
        self.buildsetid = buildsetid

    def _compute_status(self):
        # when_timestamp & submitted_at ?
        if not self.complete and not self.complete_at and not self.finish_time:  # not complete
            if self.start_time and self.claimed_at:         # running
                return self.__class__.st_running
            if not self.start_time and not self.claimed_at: # pending
                return self.__class__.st_pending
        if self.complete and self.complete_at and self.finish_time and \
            self.start_time and self.claimed_at:            # complete
            return self.__class__.st_complete
        if not self.start_time and not self.claimed_at and \
            self.complete and self.complete_at and not self.finish_time:  # cancelled
            return self.__class__.st_cancelled 
        if self.complete and self.complete_at and not self.finish_time and \
            self.start_time and self.claimed_at:            # build interrupted (eg slave disconnected) and buildbot retriggered the build
            return self.__class__.st_interrupted

        return self.__class__.st_misc                       # what's going on?

    @classmethod
    def str_status(cls, status):
        return cls._st_to_str[status]

    def get_duration(self):
        return self.complete_at - self.when_timestamp if self.complete_at and self.when_timestamp else 0
        
    def get_wait_time(self):
        return self.start_time - self.when_timestamp if self.start_time and self.when_timestamp else 0
        
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
        if br.status == BuildRequest.st_pending:
            self.pending += 1
        elif br.status == BuildRequest.st_running:
            self.running += 1
        elif br.status == BuildRequest.st_complete:
            self.complete += 1
        elif br.status == BuildRequest.st_cancelled:
            self.cancelled += 1
        elif br.status == BuildRequest.st_interrupted:
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
