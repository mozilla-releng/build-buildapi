from datetime import datetime
import math
from sqlalchemy import select, and_, or_, not_

import buildapi.model.meta as meta
from buildapi.model.reports import IntervalsReport
from buildapi.model.util import get_time_interval, get_branch_name
from buildapi.model.util import PUSHES_SOURCESTAMPS_BRANCH_SQL_EXCLUDE

import logging
log = logging.getLogger(__name__)

def PushesQuery(starttime, endtime, branches=None):
    """Constructs the sqlalchemy query for fetching all pushes in the specified
    time interval.

    One push is identified by changes.when_timestamp and branch name.
    Unittests and talos build requests are excluded.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branches - filter by list of branches, if not spefified fetches
                all branches
    Output: query
    """
    s = meta.scheduler_db_meta.tables['sourcestamps']
    sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
    c = meta.scheduler_db_meta.tables['changes']

    q = select([s.c.revision, s.c.branch, c.c.author, c.c.when_timestamp],
               and_(sch.c.changeid == c.c.changeid,
                    s.c.id == sch.c.sourcestampid))
    q = q.where(or_(
        c.c.revlink.startswith('http://hg.mozilla.org'),
        c.c.revlink.startswith('https://hg.mozilla.org'),
        c.c.comments.startswith('http://hg.mozilla.org'),
        c.c.comments.startswith('https://hg.mozilla.org')))
    q = q.group_by(c.c.when_timestamp, s.c.branch)

    # exclude branches that are not of interest
    bexcl = [not_(s.c.branch.like(p)) for p in
        PUSHES_SOURCESTAMPS_BRANCH_SQL_EXCLUDE]
    if bexcl:
        q = q.where(and_(*bexcl))

    # filter desired branches
    if branches:
        bexp = [s.c.branch.like('%' + b + '%') for b in branches]
        q = q.where(or_(*bexp))

    if starttime is not None:
        q = q.where(c.c.when_timestamp >= starttime)
    if endtime is not None:
        q = q.where(c.c.when_timestamp < endtime)

    return q

def GetPushes(starttime=None, endtime=None, int_size=0, branches=None):
    """Get pushes and statistics.

    Input: starttime - start time (UNIX timestamp in seconds), if not
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified,
                starttime plus 24 hours or current time (if starttime is not
                specified either)
           int_size - break down results per interval (in seconds), if specified
           branches - filter by list of branches, if not spefified fetches all
                branches
    Output: pushes report
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = PushesQuery(starttime, endtime, branches)
    q_results = q.execute()

    report = PushesReport(starttime, endtime, int_size=int_size,
        branches=branches)
    for r in q_results:
        branch_name = get_branch_name(r['branch'])
        stime = float(r['when_timestamp'])
        revision = r['revision']

        push = Push(stime, branch_name, revision)
        report.add(push)

    return report

class PushesReport(IntervalsReport):

    def __init__(self, starttime, endtime, int_size=0, branches=None):
        IntervalsReport.__init__(self, starttime, endtime, int_size=int_size)

        if not branches:
            self.branches = []
        else:
            self.branches = branches    # list of branches

        self.filter_branches = bool(self.branches)

        self.total = 0
        self.intervals = [0] * self.int_no
        self.branch_intervals = {}
        self.branch_totals = {}
        self.daily_intervals = [0] * 24
        self.timeframe = self.endtime - self.starttime - 1
        self.days = math.ceil(self.timeframe / 86400.)

        for b in self.branches:
            self._init_branch(b)

    def _init_branch(self, branch):
        if branch not in self.branches: self.branches.append(branch)
        self.branch_intervals[branch] = [0] * self.int_no
        self.branch_totals[branch] = 0

    def get_total(self, branch=None):
        if not branch:
            return self.total
        return self.branch_totals[branch]

    def get_intervals(self, branch=None):
        if not branch:
            return self.intervals
        return self.branch_intervals[branch]

    def add(self, push):
        if self.filter_branches and push.branch_name not in self.branches:
            return False

        if push.branch_name not in self.branches:
            self._init_branch(push.branch_name)

        int_idx = self.get_interval_index(push.stime)

        self.total += 1
        self.intervals[int_idx] += 1
        self.branch_intervals[push.branch_name][int_idx] += 1
        self.branch_totals[push.branch_name] += 1

        if push.stime:
            self.daily_intervals[datetime.fromtimestamp(push.stime).hour] += 1

        return True

    def to_dict(self, summary=False):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'int_size': self.int_size,
            'total': self.total,
            'intervals': self.intervals,
            'branch': { }
        }
        for branch in self.branch_intervals:
            json_obj['branch'][branch] = {
                'total': self.branch_totals[branch],
                'intervals': self.branch_intervals[branch]
            }

        return json_obj

class Push(object):

    def __init__(self, stime, branch_name, revision):
        self.stime = stime
        self.branch_name = branch_name
        self.revision = revision
