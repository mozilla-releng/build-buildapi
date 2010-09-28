import time, re

# Buildrequest statuses
PENDING, RUNNING, COMPLETE, CANCELLED, INTERRUPTED, MISC = range(6)

# Buildrequest results
NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(-1, 6)

BUILDPOOL_MASTERS = {
    'buildpool': [
        'production-master01.build.mozilla.org',
        'production-master03.build.mozilla.org',
        'buildbot-master1.build.scl1.mozilla.com:/builds/buildbot/build_master3',
        'buildbot-master2.build.scl1.mozilla.com:/builds/buildbot/build_master4',
    ],
    'trybuildpool': [
        'production-master02.build.mozilla.org',
    ],
    'testpool': [
        'test-master01',
        'test-master02',
        'talos-master02',
        'buildbot-master1.build.scl1.mozilla.com:/builds/buildbot/tests_master3',
        'buildbot-master1.build.scl1.mozilla.com:/builds/buildbot/tests_master4',
        'buildbot-master2.build.scl1.mozilla.com:/builds/buildbot/tests_master5',
        'buildbot-master2.build.scl1.mozilla.com:/builds/buildbot/tests_master6',
    ],
}

PLATFORMS_BUILDERNAME = {
    'linux': [re.compile('^Linux (?!x86-64).+'),
              re.compile('^Maemo 4 .+'),
              re.compile('^Maemo 5 QT .+'),
              re.compile('^Maemo 5 GTK .+'),
              re.compile('^Android R7 .+'),
             ],
    'linux64': [re.compile('^Linux x86-64 .+')],
    'fedora': [re.compile('^Rev3 Fedora 12 .+')],
    'fedora64': [re.compile('Rev3 Fedora 12x64 .+')],
    'leopard': [re.compile('^OS X 10\.5\.2 .+'),
                re.compile('^Rev3 MacOSX Leopard 10\.5\.8 .+'),
               ],
    'snowleopard': [re.compile('^OS X 10\.6\.2 .+'),
                    re.compile('^Rev3 MacOSX Snow Leopard 10\.6\.2 .+'),
                   ],
    'xp': [re.compile('^Rev3 WINNT 5\.1 .+')],
    'win2k3': [re.compile('^WINNT 5\.2 .+')],
    'win7': [re.compile('^Rev3 WINNT 6\.1 ')],
    'win764': [re.compile('^Rev3 WINNT 6\.1 x64 .+')],
}

PLATFORMS_BUILDERNAME_EXCLUDE = [
    re.compile('.+ l10n .+'),
]

PLATFORMS_BUILDERNAME_SQL_EXCLUDE = [
    'fuzzer-%',
]

SOURCESTAMPS_BRANCH = {
    'l10n-central': [re.compile('^l10n-central.*')],
    'birch': [re.compile('^birch.+'), re.compile('^projects/birch.*')],
    'cedar': [re.compile('^cedar.+'), re.compile('^projects/cedar.*')],
    'electrolysis': [re.compile('^electrolysis.*'), re.compile('^projects/electrolysis.*')],
    'jaegermonkey': [re.compile('^projects/jaegermonkey.*')],
    'maple': [re.compile('^maple.*'), re.compile('^projects/maple.*')],
    'mozilla-1.9.1': [re.compile('^mozilla-1\.9\.1.*')],
    'mozilla-1.9.2': [re.compile('^mozilla-1\.9\.2.*')],
    'mozilla-2.0': [re.compile('^mozilla-2\.0.*')],
    'mozilla-central': [re.compile('^mozilla-central.*')],
    'places': [re.compile('^places.+'), re.compile('^projects/places.*')],
    'release-mozilla-central': [re.compile('^release-mozilla-central.*')],
    'tracemonkey': [re.compile('^tracemonkey.*')],
    'try': [re.compile('^try$'), re.compile('^tryserver.*')],
}

SOURCESTAMPS_BRANCH_PUSHES_SQL_EXCLUDE = [
    '%unittest',
    '%talos',
    'addontester%',
    '%l10n%',
]

BUILDSET_REASON = {
    'forcebuild': re.compile("The web-page 'force build' button was pressed by .+"),
    'rebuild': re.compile("The web-page 'rebuild' button was pressed by .+"),
}

BUILDSET_REASON_SQL_EXCLUDE = [
    "The web-page 'force build' button was pressed by %",
    "The web-page 'rebuild' button was pressed by %",
]

BUILD_TYPE_BUILDERNAME = {
    'opt': [re.compile('.+ opt .+'), re.compile('.+ talos .+'), re.compile('.+(?<!leak test) build')],
    'debug': [re.compile('.+ debug .+'), re.compile('.+ leak test build')],
}

JOB_TYPE_BUILDERNAME = {
    'build': [re.compile('.+ build')],
    'unittest': [re.compile('.+(?<!leak) test .+')],
    'talos': [re.compile('.+ talos .+')],
}

_STATUS_TO_STR = {
    PENDING: 'PENDING',
    RUNNING: 'RUNNING',
    COMPLETE: 'COMPLETE',
    CANCELLED: 'CANCELLED',
    INTERRUPTED: 'INTERRUPTED',
    MISC: 'MISC',
}

def status_to_str(status):
    if status not in _STATUS_TO_STR: status = MISC
    return _STATUS_TO_STR[status]

_RESULTS_TO_STR = {
    NO_RESULT: '-',
    SUCCESS: 'success',
    WARNINGS: 'warnings',
    FAILURE: 'failure',
    SKIPPED: 'skipped',
    EXCEPTION: 'exception',
    RETRY: 'retry',
}

def results_to_str(results):
    if results not in _RESULTS_TO_STR: results = NO_RESULT
    return _RESULTS_TO_STR[results]

def get_branch_name(text):
    """Returns the branch name.

    Input: text - field value from schedulerdb table
    Output: branch (one in SOURCESTAMPS_BRANCH keys: mozilla-central, mozilla-1.9.1, or text if not found
    """
    if text==None: return None

    text = text.lower()
    for branch in SOURCESTAMPS_BRANCH:
        for pat in SOURCESTAMPS_BRANCH[branch]:
            if pat.match(text):
                return branch

    return text

def get_platform(buildername):
    """Returns the platform name for a buildername.

    Input: buildername - buildername field value from buildrequests schedulerdb table
    Output: platform (one in PLATFORMS_BUILDERNAME keys: linux, linux64, ...)
    """
    if any(filter(lambda p: p.match(buildername), PLATFORMS_BUILDERNAME_EXCLUDE)):
        return None

    for platform in PLATFORMS_BUILDERNAME:
        for pat in PLATFORMS_BUILDERNAME[platform]:
            if pat.match(buildername):
                return platform

    return 'other'

def get_build_type(buildername):
    """Returns the build type based on the buildername.

    Build requests are matched to a build type, depending on their job type, 
    as following: 
    * builds: 'leak test' to debug, otherwise to opt
    * unittests: 'opt' to opt, and 'debug' to debug
    * talos: always opt

    Input: buildername - buildername field value from buildrequests schedulerdb table
    Output: build type (one in BUILD_TYPE_BUILDERNAME keys: opt or debug)
    """
    for build_type in BUILD_TYPE_BUILDERNAME:
        for pat in BUILD_TYPE_BUILDERNAME[build_type]:
            if pat.match(buildername):
                return build_type

    return None

def get_job_type(buildername):
    """Returns the job type based on the buildername.

    Build requests are matched to a job type, as following:
    * build, if buildername contains 'build'
    * unittest, if buildername contains 'test', but not preceded by 'leak' (it would make it a build)
    * talos, if buildername contains 'talos'

    Input: buildername - buildername field value from buildrequests schedulerdb table
    Output: job type (one in JOB_TYPE_BUILDERNAME keys: build, unittest or talos)
    """
    for job_type in JOB_TYPE_BUILDERNAME:
        for pat in JOB_TYPE_BUILDERNAME[job_type]:
            if pat.match(buildername):
                return job_type

    return None

def get_time_interval(starttime, endtime):
    """Returns (sarttime2, endtime2) tuple, where the starttime2 is the exact 
    value of input parameter starttime if specified, or endtime minus 24 hours
    if not. endtime2 is the exact value of input parameter endtime if specified,
    or starttime plus 24 hours or current time (if starttime is not specified 
    either).

    Input: stattime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
    Output: (stattime2, endtime2)
    """
    nowtime = time.time()
    if not endtime:
        endtime = min(starttime+24*3600 if starttime else nowtime, nowtime)
    if not starttime:
        starttime = endtime-24*3600

    return starttime, endtime
