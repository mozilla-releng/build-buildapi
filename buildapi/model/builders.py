import simplejson
from sqlalchemy import or_, not_

import buildapi.model.meta as meta
from buildapi.model.buildrequest import BuildRequest, BuildRequestsQuery
from buildapi.model.util import PENDING, RUNNING, NO_RESULT, SUCCESS, \
WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY
from buildapi.model.util import BUILDERS_DETAIL_LEVELS
from buildapi.model.util import get_time_interval, get_platform, \
get_build_type, get_job_type

br = meta.scheduler_db_meta.tables['buildrequests']
c = meta.scheduler_db_meta.tables['changes']

def BuildersQuery(starttime, endtime, branch_name):
    """Constructs the sqlalchemy query for fetching all build requests in the 
    specified time interval for the specified branch.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           branch_name - branch name
    Output: query
    """
    return BuildRequestsQuery(starttime=starttime, endtime=endtime,
            branch_name=branch_name)

def BuildersTypeQuery(starttime, endtime, buildername):
    """Constructs the sqlalchemy query for fetching all build requests in the 
    specified time interval for the specified buildername.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           buildername - builder's name
    Output: query
    """
    q = BuildRequestsQuery(starttime=starttime, endtime=endtime)
    q = q.where(br.c.buildername.like(buildername))
    return q

def GetBuildersReport(starttime=None, endtime=None, branch_name='mozilla-central',
    platform=[], build_type=[], job_type=[], detail_level='builder'):
    """Get the average time per builder report for the speficied time interval 
    and branch.

    Input: starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
           branch_name - branch name, default vaue is 'mozilla-central'
    Output: BuildersReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    detail_level_no = BUILDERS_DETAIL_LEVELS.index(detail_level) + 1

    q = BuildersQuery(starttime, endtime, branch_name)
    q_results = q.execute()

    report = BuildersReport(starttime, endtime, branch_name, detail_level=detail_level_no)
    report.set_filters(dict(platform=platform, build_type=build_type, job_type=job_type))

    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        br = BuildRequest(**params)
        report.add(br)

    return report

def GetBuilderTypeReport(starttime=None, endtime=None, buildername=None):
    """Get the average time per builder report for one builder for the 
    speficied time interval. The builder is specified by its buildername.

    Input: starttime - start time (UNIX timestamp in seconds), if not 
                    specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                    starttime plus 24 hours or current time (if starttime is 
                    not specified either)
           buildername - buildername
    Output: BuilderTypeReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = BuildersTypeQuery(starttime, endtime, buildername)
    q_results = q.execute()

    report = BuilderTypeReport(buildername=buildername, starttime=starttime, endtime=endtime)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        br = BuildRequest(**params)
        report.add(br)

    return report

class Node(object):
    def __init__(self, name, info=None):
        self.name = name
        self.info = info
        self.next = {}

class BuildersReport(object):

    def __init__(self, starttime, endtime, branch_name, detail_level=4):
        self.starttime = starttime
        self.endtime = endtime
        self.branch_name = branch_name

        self.filters = dict(platform=[], build_type=[], job_type=[], buildername=[])
        self._filter_names = ('platform', 'build_type', 'job_type', 'buildername')
        self.detail_level = detail_level

        # builders tree
        self.builders = Node(self.branch_name, info=BuilderTypeReport(detail_level=0))

    def add(self, br):
        path = (br.platform, br.build_type, br.job_type, br.buildername)[:self.detail_level]

        if not self._passes_filters(path):
            return

        params = {}
        node = self.builders  # root node
        node.info.add(br)     # update root report
        for level, name in enumerate(path):
            params.update({self._filter_names[level]: name})

            # create node if it doesn't exist
            if name not in node.next:
                node.next[name] = Node(name, info=BuilderTypeReport(detail_level=level + 1, **params))

            # update report
            node = node.next[name]
            node.info.add(br, summary=True)

    def _passes_filters(self, path):
        for level, name in enumerate(path):
            filter_name = self._filter_names[level]
            if len(self.filters[filter_name]) > 0 and name not in self.filters[filter_name]:
                return False
        return True

    def get_builders(self, leafs_only=True, detail_level=None):
        max_level = min(detail_level or self.detail_level, self.detail_level)
        results = []
        self._traverse_tree(self.builders, results, leafs_only, max_level, 0)

        return results

    def get_path(self, b):
        return (b.platform, b.build_type, b.job_type, b.buildername)[:self.detail_level]

    def set_filters(self, filters):
        self.filters.update(filters)

    def _traverse_tree(self, node, blist, leafs_only, max_level, level):
        if not node or level > max_level: return
        if not leafs_only or (leafs_only and level == max_level):
            blist.append(node.info)
        for c in node.next:
            self._traverse_tree(node.next[c], blist, leafs_only, max_level, level+1)

    def get_sum_run_time(self):
        return self.builders.info.get_sum_run_time()

    def to_dict(self, summary=False, leafs_only=True, detail_level=None):
        detail_level = min(detail_level or self.detail_level, self.detail_level)
        total_sum_run_time = self.builders.info.get_sum_run_time()
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'branch_name': self.branch_name,
            'detail_level': detail_level,
            'sum_run_time': total_sum_run_time,
        }
        json_obj.update(self.filters)
        if not summary:
            json_obj['builders'] = []
            for b in self.get_builders(leafs_only=leafs_only, detail_level=detail_level):
                obj = b.to_dict(summary=True)
                obj['ptg_run_time'] = "%.2f" % \
                    (b.get_sum_run_time() * 100. / total_sum_run_time if total_sum_run_time else 0)
                json_obj['builders'].append(obj)

        return json_obj

    def jsonify(self, summary=False, leafs_only=True, detail_level=None):
        return simplejson.dumps(self.to_dict(summary=summary, 
            leafs_only=leafs_only, detail_level=detail_level))

class BuilderTypeReport(object):

    def __init__(self, buildername=None, platform=None, build_type=None, 
        job_type=None, starttime=None, endtime=None, detail_level=4):
        """If platform, build_type or job_type are not specified, they will be 
        parsed out of the buildername.
        """
        self.starttime = starttime
        self.endtime = endtime

        self.platform = platform or get_platform(buildername)
        self.build_type = build_type or get_build_type(buildername) # opt / debug
        self.job_type = job_type or get_job_type(buildername)       # build / unittest / talos
        self.buildername = buildername

        self.detail_level = detail_level

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

    def get_avg_run_time(self):
        return self._d_sum / self._total_br if self._total_br else 0

    def get_sum_run_time(self):
        return self._d_sum

    def get_min_run_time(self):
        return self._d_min if self._d_min else 0

    def get_max_run_time(self):
        return self._d_max

    def get_total_build_requests(self):
        return self._total_br

    def get_ptg_results(self):
        if not self._total_br:
            return self._total_br_results
        return dict([(r, (float(n) / self._total_br) * 100) for (r, n) in self._total_br_results.items()])

    def add(self, br, summary=False, exclude=(PENDING, RUNNING)):
        # exclude pending and running build requests
        if br.status in exclude:
            return

        d = br.get_run_time()
        if d < self._d_min or self._d_min == None: self._d_min = d
        if d > self._d_max: self._d_max = d
        self._d_sum += d

        self._total_br += 1
        if br.results in self._total_br_results:
            self._total_br_results[br.results] = self._total_br_results[br.results] + 1

        if not summary: self.build_requests.append(br)

    def to_dict(self, summary=False):
        json_obj = {
            'buildername': self.buildername or '',
            'platform': self.platform or '',
            'build_type': self.build_type or '',
            'job_type': self.job_type or '',
            'avg_run_time': self.get_avg_run_time(),
            'min_run_time': self.get_min_run_time(),
            'max_run_time': self.get_max_run_time(),
            'sum_run_time': self.get_sum_run_time(),
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
