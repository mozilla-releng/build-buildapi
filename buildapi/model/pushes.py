from sqlalchemy import select, and_, not_
import buildapi.model.meta as meta
from buildapi.model.util import get_time_interval, get_branch_name
from buildapi.model.util import SOURCESTAMPS_BRANCH, SOURCESTAMPS_BRANCH_PUSHES_SQL_EXCLUDE

import simplejson

def PushesQuery(starttime, endtime, branches=None):
    """Constructs the sqlalchemy query for fetching all pushes in the specified time interval.
    One push is identified by changes.when_timestamp and branch name.
    
    Unittests and talos build requests are excluded.
    
    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branches - filter by list of branches, if not spefified fetches all branches
    Output: query
    """
    s = meta.scheduler_db_meta.tables['sourcestamps']
    sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
    c = meta.scheduler_db_meta.tables['changes']

    q = select([s.c.revision, s.c.branch, c.c.author, c.c.when_timestamp],
               and_(sch.c.changeid == c.c.changeid, s.c.id == sch.c.sourcestampid))
    q = q.group_by(c.c.when_timestamp, s.c.branch)

    # exclude branches that are not of interest
    bexcl = [not_(s.c.branch.like(p)) for p in SOURCESTAMPS_BRANCH_PUSHES_SQL_EXCLUDE]
    if len(bexcl) > 0:
        q = q.where(and_(*bexcl))

    if branches is not None:
        for branch in branches:
            q = q.where(s.c.branch.like('%' + branch + '%'))

    if starttime is not None:
        q = q.where(c.c.when_timestamp >= starttime)
    if endtime is not None:
        q = q.where(c.c.when_timestamp < endtime)

    return q

def GetPushes(starttime=None, endtime=None, int_size=0, branches=None):
    """Get pushes and statistics.

    Input: starttime - start time (UNIX timestamp in seconds), if not specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, starttime plus 24 hours or 
                     current time (if starttime is not specified either)
           int_size - break down results per interval (in seconds), if specified
           branches - filter by list of branches, if not spefified fetches all branches
    Output: pushes report
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = PushesQuery(starttime, endtime, branches)
    q_results = q.execute()

    report = PushesReport(starttime, endtime, int_size=int_size, branches=branches)
    for r in q_results:
        branch_name = get_branch_name(r['branch'])
        stime = float(r['when_timestamp'])
        revision = r['revision']

        push = Push(stime, branch_name, revision)
        report.add(push)

    return report

class PushesReport(object):

    def __init__(self, starttime, endtime, int_size=0, branches=None):
        self.starttime = starttime
        self.endtime = endtime
        self.int_size = int_size
        self.branches = branches or []
        
        self.filter_branches = bool(self.branches)
        self._init_report()

    def _init_report(self):
        self.total = 0
        self.int_no = int((self.endtime-self.starttime-1)/self.int_size)+1 if self.int_size else 1
        self.intervals = [0]*self.int_no
        self.branch_intervals = {}
        self.branch_totals = {}

        for b in self.branches: self._init_branch(b)

    def _init_branch(self, branch):
        if branch not in self.branches: self.branches.append(branch)
        self.branch_intervals[branch] = [0]*self.int_no
        self.branch_totals[branch] = 0

    def get_total(self, branch=None):
        if not branch: return self.total
        return self.branch_totals[branch]

    def get_interval_timestamp(self, int_idx):
        return self.starttime + int_idx*self.int_size

    def get_interval_index(self, stime):
        t = stime - self.starttime if stime > self.starttime else 0
        return int(t/self.int_size) if self.int_size else 0

    def get_intervals(self, branch=None):
        if not branch: return self.intervals
        return self.branch_intervals[branch]

    def add(self, push):
        if self.filter_branches and push.branch_name not in self.branches: 
            return False

        if push.branch_name not in self.branches:
            self._init_branch(push.branch_name)

        int_idx = self.get_interval_index(push.stime)

        self.total+=1
        self.intervals[int_idx]+=1
        self.branch_intervals[push.branch_name][int_idx]+=1
        self.branch_totals[push.branch_name]+=1

        return True

    def to_dict(self, summary=False):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'int_size': self.int_size,
            'total': self.total,
            'intervals': self.intervals,
            'branches': { }
        }
        for branch in self.branch_intervals:
            json_obj['branches'][branch] = {
                'total': self.branch_totals[branch], 
                'intervals': self.branch_intervals[branch]
            }

        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))

class Push(object):

    def __init__(self, stime, branch_name, revision):
        self.stime = stime
        self.branch_name = branch_name
        self.revision = revision
