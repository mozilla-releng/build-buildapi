import simplejson
from sqlalchemy import or_

import buildapi.model.meta as meta
from buildapi.model.buildrequest import BuildRequest, BuildRequestsQuery, GetBuildRequests
from buildapi.model.changes import GetChanges
from buildapi.model.util import BUILDSET_REASON, PENDING, RUNNING, COMPLETE, \
CANCELLED, INTERRUPTED, MISC
from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, \
SKIPPED, EXCEPTION, RETRY
from buildapi.model.util import get_time_interval, get_branch_name, \
get_platform, get_build_type, get_job_type, get_revision, results_to_str

br = meta.scheduler_db_meta.tables['buildrequests']
s = meta.scheduler_db_meta.tables['sourcestamps']
c = meta.scheduler_db_meta.tables['changes']

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

    report = EndtoEndTimesReport(starttime, endtime, branch_name)

    build_requests = GetBuildRequests(branch_name=branch_name, 
        starttime=starttime, endtime=endtime, changeid_all=True)
    for key in build_requests:
        report.add_build_request(build_requests[key])

    changes = GetChanges(branch_name=branch_name, starttime=starttime, 
        endtime=endtime)
    report.parse_incomplete(changes)

    return report

def GetBuildRun(branch_name=None, revision=None):
    """Get build run report. The build run report is specified by its 
    sourcestamps.revision number.

    Input: branch_name - branch name
           revision - sourcestamps.revision (first 12 chars are enough), or 
                None for nigthtlies
    Output: BuildRun
    """
    revision = get_revision(revision)

    report = BuildRun(revision, branch_name)

    build_requests = GetBuildRequests(revision=revision,
        branch_name=branch_name, changeid_all=True)
    brun_changeids = set()
    for key in build_requests:
        br = build_requests[key]
        report.add(br)

        for cid in br.changeid:
            brun_changeids.add(cid)

    changes = GetChanges(branch_name=branch_name, revision=revision)
    # filter out changes without build requests
    for cid in changes:
        if cid not in brun_changeids:
            report.set_incomplete(change=changes[cid])

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
        self._changes = set()
        self.pending_changes = {}
        # _changes_revision_runs - extra links to build run, if Build Run has 
        # Build Requests with changes.revision other than sourcestamps.revision
        self._changes_revision_runs = {}
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

    def parse_incomplete(self, changes):
        """For any change in changes list that has no build request created,
        find the most likely build run it will belong to and mark is as 
        incomplete. Also memorize these changes into self.pending_changes.
        """
        for cid in changes:
            if cid not in self._changes:
                c = changes[cid]
                run = None
                if c.revision in self._runs:
                    run = self._runs[c.revision]
                elif c.revision in self._changes_revision_runs:
                    run = self._changes_revision_runs[c.revision]

                if run:
                    run.set_incomplete(change=c)
                    c.ss_revision = run.revision
                    self.pending_changes[cid] = c

    def add_build_request(self, br):
        if br.revision not in self._runs:
            self._runs[br.revision] = BuildRun(br.revision, br.branch_name)
        run = self._runs[br.revision]
        run.add(br)

        # keep references to build run for changes.revision too
        if br.revision != br.changes_revision:
            if br.changes_revision not in self._changes_revision_runs:
                self._changes_revision_runs[br.changes_revision] = run
        # keep list of all changeid-s that have build requests
        for changeid in br.changeid:
            self._changes.add(changeid)

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
        self.changes_revision = set()
        self.authors = set()

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

        self.unittests = 0
        self.talos = 0
        self.builds = 0

        self.results_success = 0
        self.results_warnings = 0
        self.results_failure = 0
        self.results_other = 0
        self.results = NO_RESULT

        # incomplete flag (if true, BuildRun is incomplete)
        self.f_incomplete = False
        self.pending_changes = []

    def add(self, br):
        self.build_requests.append(br)

        self.changes_revision.add(br.changes_revision)
        for auth in br.authors:
            self.authors.add(auth)

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
                self.unittests += 1
            elif br.branch.endswith('talos'):
                self.talos += 1
            else:
                self.builds += 1

    def get_duration(self):
        return self.gst_complete_at_time - self.lst_change_time if self.gst_complete_at_time and self.lst_change_time else 0

    def get_total_build_requests(self):
        return self._total_br

    def get_unique_total_build_requests(self):
        if self._u_total_br == BuildRun.outdated:
            self._u_total_br = len(set([br.brid for br in self.build_requests]))

        return self._u_total_br

    def set_incomplete(self, incomplete=True, change=None):
        self.f_incomplete = incomplete
        if incomplete and change:
            self.pending_changes.append(change)

    def is_complete(self):
        return not(self.f_incomplete or self.running or self.pending)

    def to_dict(self, summary=False):
        json_obj = {
            'revision': self.revision,
            'changes_revision': [rev if rev else 'None' for rev in self.changes_revision],
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
            'builds': self.builds,
            'unittests': self.unittests,
            'talos': self.talos,
            'authors': [auth for auth in self.authors if auth],
        }
        if not summary:
            json_obj['build_requests'] = [br.to_dict() for br in self.build_requests]

        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))
