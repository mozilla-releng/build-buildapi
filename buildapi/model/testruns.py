from sqlalchemy import *
from sqlalchemy.sql import func
import buildapi.model.meta as meta
from buildapi.model.util import get_time_interval
from pylons.decorators.cache import beaker_cache

import re, simplejson, datetime

PLATFORMS_BUILDERNAME = {
    'linux': [re.compile('.+linux-.*'),
              re.compile('.+\-linux$'),
             ],
    'linux64': [re.compile('.+linux64.*')],
    'fedora': [re.compile('.+fedora-.+'),
               re.compile('.+\-fedora$'),
               re.compile('.+_fedora_test.*')
              ],
    'fedora64': [re.compile('.+fedora64.*'),
                 re.compile('.+_fedora64_test.*')
                ],
    'leopard': [re.compile('.+leopard.*'),
                re.compile('.+_leopard_test.*')
               ],
    'snowleopard': [re.compile('.+snowleopard.*'),
                    re.compile('.+_snowleopard.*')
                   ],
    'lion': [re.compile('.+lion.*'),
             re.compile('.+_lion.*')
            ],
    'xp': [re.compile('.+_xp_test.*'),
           re.compile('.+xp.*')],
    'xp-ix': [re.compile('.+_xp-ix_test.*'),
              re.compile('.+xp-ix.*')],
    'win7': [re.compile('.+_win7_test.*'),
             re.compile('.+\win7.*')],
    'win7-ix': [re.compile('.+_win7-ix_test.*'),
             re.compile('.+\win7-ix.*')],
    'win764': [re.compile('.+_w764_test.*'),
               re.compile('.+w764.*')],
    'win8': [re.compile('.+_win8_test.*'),
             re.compile('.+\win8.*')],
}

ALL_BRANCHES = (
    "mozilla-central",
    "tryserver",
    "release-mozilla-central",
    "mozilla-1.9.1",
    "mozilla-1.9.2",
    "mozilla-2.0",
    "birch",
    "cedar",
    "electrolysis",
    "jaegermonkey",
)

test_strings = (
    "crashtest",
    "reftest",
    "xpcshell",
    "jsreftest",
    "Run performance tests",
    "mochitest-chrome",
    "mochitest-browser-chrome",
    "mochitest-a11y",
    "mochitest-ipcplugins",
)

exclusions = (
     "mozilla-central-linux-codecoverage",
)

test_strings_partial = (
    "%mochitest-plain%"
)

test_suites = (
    "crashtest",
    "reftest",
    "xpcshell",
    "jsreftest",
    "mochitest-other",
    "mochitest-browser-chrome",
    "mochitest-1",
    "mochitest-2",
    "mochitest-3",
    "mochitest-4",
    "mochitest-5",
    "chrome",
    "nochrome"
    "scroll",
    "a11y",
    "tp4",
    "svg",
    "dirty",
    "v8",
    "cold",
    "dromaeo",
    "addon",
)

build_types = (
    "debug",
    "opt",
)

def TestRunsQuery(starttime, endtime, category):
    """Constructs the sqlalchemy query for fetching all pushes in the specified time interval.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           category - filter by list of builder categories, if not spefified fetches all builder categories
    Output: query
    """
    bldrs  = meta.status_db_meta.tables['builders']
    blds   = meta.status_db_meta.tables['builds']
    stps   = meta.status_db_meta.tables['steps']
    #construct an aliased subquery that grabs a list of test jobs with 'build' ids, buildernames, total jobtimes, and total actual testing time
    sq = subquery('a', [blds.c.id,
                bldrs.c.name.label("name"),
                func.timestampdiff(text('SECOND'), blds.c.starttime, blds.c.endtime).label("total"),
                func.sum(func.timestampdiff(text('SECOND'), stps.c.starttime, stps.c.endtime)).label("test")],
                and_(blds.c.id==stps.c.build_id, blds.c.builder_id==bldrs.c.id, #inner join on builds, builders and steps
                     or_(stps.c.name.like(test_strings_partial),
                         stps.c.name.in_(test_strings)),
                     blds.c.result.in_((1, 0)), # only grab successful jobs
                     not_(bldrs.c.name.in_(exclusions)),
                     bldrs.c.category == category if category else bldrs.c.category.in_(ALL_BRANCHES), #filter by given category
                     blds.c.endtime > blds.c.starttime,
                     blds.c.starttime >= datetime.date.fromtimestamp(starttime).strftime("%Y%m%d"), #filter by daterange
                     blds.c.endtime <= datetime.date.fromtimestamp(endtime).strftime("%Y%m%d"),
                     func.timestampdiff(text('SECOND'), blds.c.starttime, blds.c.endtime) < 86400, # discard massive outliers
                     func.timestampdiff(text('SECOND'), blds.c.starttime, blds.c.endtime) > 10,    # jobs taking >1 day, <10s
                    ),
                group_by=(stps.c.build_id),
              )
    #aggregate data from subquery into a list of averages for each builder (buildername, average total job time, average actual testing time)
    q = select([sq.c.name, func.avg(sq.c.total).label("total"), func.avg(sq.c.test).label("test")],
                group_by=(sq.c.name),
                order_by=( (func.avg(sq.c.test)/func.avg(sq.c.total)).asc() ),
               )

    return q
# So that nose doesn't think this is a test case...
TestRunsQuery.__test__ = False


def GetTestRuns(starttime=None, endtime=None, int_size=0, category=None, platform=None, group=False, btype=None):
    """Get test run metrics for a given interval
    Input: starttime - start time (UNIX timestamp in seconds), if not specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, starttime plus 24 hours
                     current time (if starttime is not specified either)
           int_size - break down results per interval (in seconds), if specified
           category - filter by list of builder categories, if not specified fetches all categories
           platform - filter by platform, if not specified, fetch all platforms
           group    - group results together by test suite if specified, otherwise fetch all builders uniquely
           btype    - filter by build type (opt/debug/etc), if not specified, return all
    Output: pushes report
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    q = TestRunsQuery(starttime, endtime, category=category)
    q_results = q.execute()
    report = TestRunsReport(starttime, endtime, category=category, platform=platform, group=group, btype=btype)
    filtered_results = []
    #filter by platform, build type
    if platform and btype:
        filtered_results = filter(lambda x: platform == get_platform(x['name']) and btype == get_build_type(x['name']), q_results)
    elif platform and not btype:
        filtered_results = filter(lambda x: platform == get_platform(x['name']), q_results)
    elif btype and not platform:
        filtered_results = filter(lambda x: btype == get_build_type(x['name']), q_results)
    else:
        filtered_results = list(q_results)

    if group:
        for test in test_suites:
            grouped_results = filter(lambda p: p['name'].find(test)>-1, filtered_results)
            if grouped_results:
                average_total   = reduce(lambda x, y: x + y, map(lambda x: x['total'], grouped_results)) / len(grouped_results)
                average_test    = reduce(lambda x, y: x + y, map(lambda x: x['test'], grouped_results)) / len(grouped_results)
                row = { 'total': int(average_total),
                        'test' : int(average_test),
                        'ratio': average_test/average_total,
                        'platform': platform,
                      }
                report.add(test, row)
    else:
        for r in filtered_results:
            this_row = { 'total':r['total'],
                         'test':r['test'],
                         'ratio':r['test']/r['total'],
                         'platform': get_platform(r['name']),
                       }
            report.add(r['name'], this_row)

    return report


class TestRunsReport(object):
    # So that nose doesn't think this is a test case...
    __test__ = False

    def __init__(self, starttime, endtime, builders=None, category=None, platform=None, group=False, btype=None):
        self.starttime = starttime
        self.endtime = endtime
        self.total = 0
        self.builders = builders or {}
        self.category = category or 'ALL'
        self.platform = platform or 'ALL'
        self.btype = btype or 'ALL'
        self.group = group
        self.categories = ALL_BRANCHES
        self.platforms  = PLATFORMS_BUILDERNAME.keys()
        self.build_types = build_types


    def add(self, builder, testrun):
        self.builders[builder] = testrun
        self.total+=1
        return True

    def get_total_time(self, builder):
        return int(self.builders[builder]['total'])

    def get_test_time(self, builder):
        return int(self.builders[builder]['test'])

    def get_ratio(self, builder):
        return "%.3f" % (self.builders[builder]['ratio'])

    def get_platform(self, builder):
        return self.builders[builder]['platform']

    def jsonify(self):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'total': int(self.total),
            'category': self.category,
            'btype': self.btype,
            'group': self.group,
            'builders': { }
        }
        for builder in self.builders:
            json_obj['builders'][builder] = {
                'total': self.get_total_time(builder),
                'test': self.get_test_time(builder),
                'ratio': str(self.get_ratio(builder)),
                'platform': self.get_platform(builder),
            }

        return simplejson.dumps(json_obj)

def get_platform(buildername):
    """Returns the platform name for a buildername.

    Input: buildername - buildername field value from builders status_db table
    Output: platform (one in PLATFORMS_BUILDERNAME keys: linux, linux64, ...)
    """
    bname = buildername.lower()

    for platform in PLATFORMS_BUILDERNAME:
        for pat in PLATFORMS_BUILDERNAME[platform]:
            if pat.match(buildername):
                return platform

    return 'other'

def get_build_type(buildername):
    """Returns the build type (opt/debug/etc) for a given buildername
    Input: buildername - buildername field value from builders status_db table
    Output: build type (str)
    """
    bname = buildername.lower()
    for btype in build_types:
        if (bname.find(btype)>-1):
            return btype

    return 'other'

