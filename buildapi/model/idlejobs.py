from sqlalchemy import *
from sqlalchemy.sql import func
import buildapi.model.meta as meta
from buildapi.model.util import get_time_interval
from pylons.decorators.cache import beaker_cache
from decimal import *
import re, simplejson, datetime

def IdleJobsQuery(starttime, endtime):
    """Constructs the sqlalchemy query for fetching all idlejobs jobs in the specified time interval.
    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
    Output: query
    """
    bldrs  = meta.status_db_meta.tables['builders']
    blds   = meta.status_db_meta.tables['builds']
    q = select([bldrs.c.name.label('name'),
                blds.c.starttime.label('starttime'),
                blds.c.endtime.label('endtime'),
               ],
               and_(
                     bldrs.c.id==blds.c.builder_id,
                     bldrs.c.category.like('%idle%'),
                     blds.c.starttime>datetime.date.fromtimestamp(starttime).strftime("%Y%m%d"),
                     blds.c.endtime<datetime.date.fromtimestamp(endtime).strftime("%Y%m%d"),
                     blds.c.endtime>blds.c.starttime
                   ),
              )
    return q

def GetTimeStamp(date_time):
    return int(date_time.strftime("%s"))

def GetIdleJobsReport(starttime=None, endtime=None, int_size=0):
    """Get test metrics for idlejobs jobs in a given time interval
    Input: starttime - start time (UNIX timestamp in seconds), if not specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, starttime plus 24 hours
                     current time (if starttime is not specified either)
           int_size - break down results per interval (in seconds), if specified
    Output: idlejobs report
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    q = IdleJobsQuery(starttime, endtime)
    q_results = q.execute()
    report = IdleJobsReport(starttime, endtime, int_size)

    for r in q_results:
            this_row = {
                         'starttime': GetTimeStamp(r['starttime']),
                         'endtime'  : GetTimeStamp(r['endtime']),
                       }
            report.add(r['name'], this_row)
    return report


class IdleJobsReport(object):
    def __init__(self, starttime, endtime, int_size=0, builders=None):
        self.starttime = starttime
        self.endtime = endtime
        self.total = 0
        self.builders = builders or []
        self.int_size = int_size
        self.int_no = int((self.endtime - self.starttime-1)/self.int_size) +1 if self.int_size else 1
        self.builder_intervals = {}
        self.builder_intervals['Total'] = [0]*self.int_no
        self.totals = {}
        self.totals['Total'] = 0

    def get_interval_timestamp(self, int_idx):
        return self.starttime + int_idx*self.int_size

    def get_interval_indices(self, stime, etime):
        t = stime - self.starttime if stime > self.starttime else 0
        first_interval = int(t/self.int_size) if self.int_size else 0
        t = etime - self.starttime if etime > self.starttime else 0
        last_interval = int(t/self.int_size) if self.int_size else 0
        return range(first_interval, last_interval+1)

    def add(self, builder, row):
        int_idxs = self.get_interval_indices(row['starttime'], row['endtime'])
        if builder not in self.builders:
            self.builders.append(builder)
            self.builder_intervals[builder] = [0]*self.int_no
            self.totals[builder] = 0

        self.totals[builder] += row['endtime']-row['starttime']
        self.totals['Total'] += row['endtime']-row['starttime']
        for i in int_idxs:
            self.builder_intervals[builder][i] += 1
            self.builder_intervals['Total'][i] += 1
        self.total+=1
        return True

    def jsonify(self):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'int_size': self.int_size,
            'total': self.total,
            'builders': { }
        }
        for builder in self.builders:
           json_obj['builders'][builder] = {
               'intervals': self.builder_intervals[builder],
               'total compute time': int(self.totals[builder]),
           }

        return simplejson.dumps(json_obj)

