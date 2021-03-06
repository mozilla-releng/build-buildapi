import math
from sqlalchemy import outerjoin, and_, not_, or_, func

from buildapi.lib.helpers import get_masters_for_pool
import buildapi.model.meta as meta
from buildapi.model.reports import IntervalsReport
from buildapi.model.util import get_time_interval, get_platform
from buildapi.model.util import WAITTIMES_BUILDSET_REASON_SQL_EXCLUDE, \
WAITTIMES_BUILDREQUESTS_BUILDERNAME_SQL_EXCLUDE, \
WAITTIMES_BUILDREQUESTS_BUILDERNAME_EXCLUDE

def WaitTimesQuery(starttime, endtime, pool):
    """Constructs the sqlalchemy query for fetching all wait times for a 
    buildpool in the specified time interval.

    Input: pool - name of the pool (e.g. buildpool, or trybuildpool)
           starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           pool - fetches the builds only for masters in pool
    Output: query
    """
    b  = meta.scheduler_db_meta.tables['builds']
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    s = meta.scheduler_db_meta.tables['sourcestamps']
    sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
    c = meta.scheduler_db_meta.tables['changes']

    q = outerjoin(br, b, b.c.brid == br.c.id) \
            .join(bs, bs.c.id == br.c.buildsetid) \
            .join(s, s.c.id == bs.c.sourcestampid) \
            .outerjoin(sch, sch.c.sourcestampid == s.c.id) \
            .outerjoin(c, c.c.changeid == sch.c.changeid) \
            .select() \
            .with_only_columns([
                br.c.buildername,
                br.c.claimed_at,
                br.c.submitted_at,
                func.min(b.c.start_time).label("start_time"),
                func.min(c.c.when_timestamp).label("when_timestamp"),
            ])

    q = q.where(bs.c.submitted_at >= starttime)
    q = q.where(bs.c.submitted_at < endtime)

    # filter by masters
    masters = get_masters_for_pool(pool)
    mnames_matcher = [br.c.claimed_by_name.startswith(master) 
        for master in masters]
    if mnames_matcher:
        pending_matcher_clause = get_pending_buildrequests_query_clause(br, pool)
        q = q.where(or_(pending_matcher_clause, *mnames_matcher))

    # exclude all rebuilds and forced builds
    rmatcher = [not_(bs.c.reason.like(rpat)) \
        for rpat in WAITTIMES_BUILDSET_REASON_SQL_EXCLUDE]
    if rmatcher:
        q = q.where(and_(*rmatcher))

    # exclude pushes which are DONTBUILD
    q = q.where(not_(c.c.comments.like("%DONTBUILD%")))

    # exclude unrelated buildrequests.buildername-s
    bmatcher = [not_(br.c.buildername.like(rpat)) \
        for rpat in WAITTIMES_BUILDREQUESTS_BUILDERNAME_SQL_EXCLUDE]
    if bmatcher:
        q = q.where(and_(*bmatcher))

    # get one change per sourcestamp and platform
    # (ingnore multiple changes in one push)
    q = q.group_by(br.c.id)

    return q

def GetWaitTimes(pool='buildpool', mpb=15, starttime=None, endtime=None,
    int_size=0, maxb=0):
    """Get wait times and statistics for buildpool.

    Input: pool - name of the pool (e.g. buildpool, or trybuildpool)
           mpb - minutes per block, length of wait time block in minutes
           starttime - start time (UNIX timestamp in seconds), if not 
                    specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                    starttime plus 24 hours or current time (if starttime is 
                    not specified either)
           int_size - break down results per interval (in seconds), if specified
           maxb - maximum block size; for wait times larger than maxb, group 
                    into the largest block
    Output: wait times report
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = WaitTimesQuery(starttime, endtime, pool)
    q_results = q.execute()

    report = WaitTimesReport(pool, starttime, endtime, mpb=mpb, maxb=maxb, 
        int_size = int_size, masters=get_masters_for_pool(pool))
    for r in q_results:
        buildername = r['buildername']
        # start time is changes.when_timestamp, or buildrequests.submitted_at 
        # if build has no changes
        stime = r['when_timestamp'] or r['submitted_at']
        etime = r['start_time']

        platform = get_platform(buildername)
        has_no_changes = not bool(r['when_timestamp'])

        wt = WaitTime(stime, etime, platform, buildername=buildername,
                      has_no_changes=has_no_changes)
        report.add(wt)

    return report

class WaitTimesReport(IntervalsReport):

    def __init__(self, pool, starttime, endtime, mpb=15, maxb=0, int_size=0, 
        masters=None):
        IntervalsReport.__init__(self, starttime, endtime, int_size=int_size)

        self.pool = pool
        self.masters = masters or get_masters_for_pool(pool)

        self.mpb = mpb
        self.maxb = int(maxb / mpb) * mpb  # normalize

        self.otherplatforms = set()
        self.unknownbuilders = set()

        self._init_report()

    def _init_report(self):
        self.total = 0

        self.no_changes = 0  # build requests with no revision number (e.g. nightly builds)
        self.pending = []    # jobs that have not started yet

        self._wait_times = {0: WaitTimeIntervals(self.int_no)}
        self._platform_wait_times = {}
        self._platform_totals = {}

    def get_total(self, platform=None):
        if not platform: 
            return self.total
        return self._platform_totals[platform]

    def get_platforms(self):
        return self._platform_totals.keys()

    def get_blocks(self, platform=None):
        wt = self._wait_times \
            if not platform else self._platform_wait_times[platform]
        return range(0, max(wt.keys()) + 1, self.mpb)

    def get_wait_times(self, block_no, platform=None):
        wt = self._wait_times \
            if not platform else self._platform_wait_times[platform]
        return wt.get(block_no, WaitTimeIntervals(self.int_no))

    def add(self, wt):
        if self._is_unknownbuilder(wt.buildername):  # excluded
            self.unknownbuilders.add(wt.buildername)
            return

        if not wt.etime:              # job has not started yet (still waiting)
            self.pending.append(wt.buildername)  
            return

        if wt.platform == 'other':    # other platforms (NOT excluded)
            self.otherplatforms.add(wt.buildername)

        if wt.has_no_changes: self.no_changes += 1

        block_no = self._get_block_no(wt.stime, wt.etime)
        int_idx = self.get_interval_index(wt.stime)
        self._update_wait_times(wt.platform, block_no, int_idx)

    def _is_unknownbuilder(self, buildername):
        if any(filter(lambda p: p.match(buildername), 
            WAITTIMES_BUILDREQUESTS_BUILDERNAME_EXCLUDE)):
            return True

        return False

    def _get_block_no(self, stime, etime):
        span = (etime - stime) / 60.0 if stime <= etime else 0
        block_no = int(math.floor(span / self.mpb)) * self.mpb
        if self.maxb: 
            block_no = min(block_no, self.maxb)

        return block_no

    def _update_wait_times(self, platform, block_no, int_idx):
        # update overall wait times
        self.total += 1
        if block_no not in self._wait_times:
            self._wait_times[block_no] = WaitTimeIntervals(self.int_no)
        self._wait_times[block_no].update(int_idx)

        # update platform specific wait times
        self._platform_totals[platform] = \
            self._platform_totals.get(platform, 0) + 1

        if platform not in self._platform_wait_times:
            self._platform_wait_times[platform] = \
                {0: WaitTimeIntervals(self.int_no)}
        if block_no not in self._platform_wait_times[platform]:
            self._platform_wait_times[platform][block_no] = \
                WaitTimeIntervals(self.int_no)

        self._platform_wait_times[platform][block_no].update(int_idx)

    def to_dict(self, summary=False):
        json_obj = {
            'pool': self.pool,
            'masters': self.masters,
            'starttime': self.starttime,
            'endtime': self.endtime,
            'int_size': self.int_size,
            'mpb': self.mpb,
            'maxb': self.maxb,
            'no_changes': self.no_changes,
            'otherplatforms': list(self.otherplatforms), 
            'unknownbuilders': list(self.unknownbuilders),
            'pending': self.pending,
            'total': self.total,
            'wt': {},
            'platforms': {}
        }
        for block_no in self.get_blocks():
            json_obj['wt'][block_no] = self.get_wait_times(block_no).to_dict()

        for platform in self.get_platforms():
            json_obj['platforms'][platform] = {
                'total': self.get_total(platform=platform), 
                'wt':{}
            }
            for block_no in self.get_blocks(platform=platform):
                json_obj['platforms'][platform]['wt'][block_no] = \
                    self.get_wait_times(block_no, platform=platform).to_dict()

        return json_obj

class WaitTimeIntervals(object):

    def __init__(self, int_no):
        self.total = 0
        self.intervals = [0] * int_no

    def update(self, idx):
        self.total += 1
        self.intervals[idx] += 1

    def to_dict(self):
        return {'total': self.total, 'intervals': self.intervals}

class WaitTime(object):

    def __init__(self, stime, etime, platform, buildername=None, 
        has_no_changes=False):
        self.stime = stime
        self.etime = etime
        self.platform = platform
        self.buildername = buildername
        self.has_no_changes = has_no_changes

def get_pending_buildrequests_query_clause(br_table, pool):
    """Pending jobs don't have buildrequests.claimed_by_name specified, 
    therefore we need to catch the pool it belongs to by looking at 
    buildrequests.buildername fields:
        - buildpool: br.claimed_by_name == None and br.buildername NOT LIKE 
                Rev3% and NOT LIKE % tryserver %
        - trybuildpool: br.claimed_by_name == None and br.buildername NOT LIKE 
                Rev3% and LIKE % tryserver %
        - testpool: br.claimed_by_name == None and br.buildername LIKE Rev3%
    """
    if pool == 'buildpool':
        return and_(br_table.c.claimed_by_name==None, br_table.c.complete==0,
            not_(br_table.c.buildername.like('Rev3%')),
            not_(br_table.c.buildername.like('% tryserver %')))
    elif pool == 'trybuildpool':
        return and_(br_table.c.claimed_by_name==None, br_table.c.complete==0,
             not_(br_table.c.buildername.like('Rev3%')),
             br_table.c.buildername.like('% tryserver %'))
    elif pool == 'testpool':
        return and_(br_table.c.claimed_by_name==None, br_table.c.complete==0,
               br_table.c.buildername.like('Rev3%'))

    return None
