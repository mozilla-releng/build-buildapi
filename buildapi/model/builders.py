from sqlalchemy import or_, not_
import buildapi.model.meta as meta
from buildapi.model.util import PENDING, RUNNING, NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY
from buildapi.model.util import get_time_interval, get_platform, get_build_type, get_job_type
from buildapi.model.endtoend import BuildRequest, EndtoEndTimesQuery, BuildRequestsQuery

import simplejson

br = meta.scheduler_db_meta.tables['buildrequests']
c = meta.scheduler_db_meta.tables['changes']

def BuildersQuery(starttime, endtime, branch_name):
    """Constructs the sqlalchemy query for fetching all build requests in the specified time 
    interval for the specified branch.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branch_name - branch name
    Output: query
    """
    return EndtoEndTimesQuery(starttime, endtime, branch_name)

def BuildersTypeQuery(starttime, endtime, buildername):
    """Constructs the sqlalchemy query for fetching all build requests in the specified time 
    interval for the specified buildername.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branch_name - branch name
    Output: query
    """
    q = BuildRequestsQuery().where(br.c.buildername.like(buildername))

    if starttime:
        q = q.where(or_(c.c.when_timestamp>=starttime, br.c.submitted_at>=starttime))
    if endtime:
        q = q.where(or_(c.c.when_timestamp<endtime, br.c.submitted_at<endtime))

    return q

def GetBuildersReport(starttime=None, endtime=None, branch_name='mozilla-central'):
    """Get the average time per builder report for the speficied time interval and branch.

    Input: starttime - start time (UNIX timestamp in seconds), if not specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, starttime plus 24 hours or 
                     current time (if starttime is not specified either)
           branch_name - branch name, default vaue is 'mozilla-central'
    Output: BuildersReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = BuildersQuery(starttime, endtime, branch_name)
    q_results = q.execute()

    report = BuildersReport(starttime, endtime, branch_name)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        params['revision'] = params['revision'][:12] if params['revision'] else params['revision']

        br = BuildRequest(**params)
        report.add(br)

    return report

def GetBuilderTypeReport(starttime=None, endtime=None, buildername=None):
    """Get the average time per builder report for one builder for the speficied time interval.
    The builder is specified by its buildername.

    Input: starttime - start time (UNIX timestamp in seconds), if not specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, starttime plus 24 hours or 
                     current time (if starttime is not specified either)
           buildername - buildername
    Output: BuilderTypeReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = BuildersTypeQuery(starttime, endtime, buildername)
    q_results = q.execute()    

    report = BuilderTypeReport(buildername, starttime=starttime, endtime=endtime)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        params['revision'] = params['revision'][:12] if params['revision'] else params['revision']

        br = BuildRequest(**params)
        report.add(br)

    return report

class BuildersReport(object):

    def __init__(self, starttime, endtime, branch_name):
        self.starttime = starttime
        self.endtime = endtime
        self.branch_name = branch_name

        self._init_report()

    def _init_report(self):
        self.builders = {}
        self.builders_tree = {}
        self._d_sum = 0

    def add(self, br):
        #if br.platform 
        if br.buildername not in self.builders: 
            self.builders[br.buildername] = BuilderTypeReport(br.buildername)

        self.builders[br.buildername].add(br)
        self._d_sum += br.get_duration()

    def get_sum_duration(self):
        return self._d_sum

    def to_dict(self, summary=False):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'branch_name': self.branch_name,
            'builders': {},
        }
        for b in self.builders:
            json_obj['builders'][b] = self.builders[b].to_dict(summary=True)

        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))

class BuilderTypeReport(object):

    def __init__(self, buildername, starttime=None, endtime=None):
        self.starttime = starttime
        self.endtime = endtime
        self.buildername = buildername

        self.platform = get_platform(buildername)
        self.build_type = get_build_type(buildername) # opt / debug
        self.job_type = get_job_type(buildername)     # build / unittest / talos

        self.build_requests = []

        self._d_min = None
        self._d_max = 0
        self._d_sum = 0
        self._total_br_results = {
            NO_RESULT: 0,
            SUCCESS: 0,
            WARNINGS: 0,
            FAILURE: 0,
            SKIPPED: 0,
            EXCEPTION: 0,
            RETRY: 0,
        }
        self._total_br = 0

    def get_avg_duration(self):
        return self._d_sum / self._total_br if self._total_br else 0

    def get_sum_duration(self):
        return self._d_sum

    def get_min_duration(self):
        return self._d_min

    def get_max_duration(self):
        return self._d_max

    def get_total_build_requests(self):
        return self._total_br

    def get_ptg_results(self):
        if not self._total_br:
            return self._total_br_results
        return dict([(r, (float(n)/self._total_br)*100) for (r, n) in self._total_br_results.items()])

    def add(self, br):
        # exclude pending and running build requests
        if br.status in (PENDING, RUNNING):
            return

        d = br.get_duration()
        if d < self._d_min or self._d_min == None: self._d_min = d
        if d > self._d_max: self._d_max = d
        self._d_sum += d

        self._total_br += 1
        if br.results in self._total_br_results:
            self._total_br_results[br.results] = self._total_br_results[br.results] + 1

        self.build_requests.append(br)

    def to_dict(self, summary=False):
        json_obj = {
            'buildername': self.buildername,
            'platform': self.platform,
            'build_type': self.build_type,
            'job_type': self.job_type,
            'avg_duration': self.get_avg_duration(),
            'min_duration': self.get_min_duration(),
            'max_duration': self.get_max_duration(),
            'total_build_requests': self.get_total_build_requests(),
        }
        if not summary:
            json_obj.update({
                'starttime': self.starttime,
                'endtime': self.endtime,
                'build_requests': [br.to_dict() for br in self.build_requests]
            })

        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))
