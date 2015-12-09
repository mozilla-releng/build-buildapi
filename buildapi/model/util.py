import re
import time

# Masters build pools
BUILDPOOL = 'buildpool'
TRYBUILDPOOL = 'trybuildpool'
TESTPOOL = 'testpool'
POOLS = [BUILDPOOL, TRYBUILDPOOL, TESTPOOL]

# Buildrequest statuses
PENDING, RUNNING, COMPLETE, CANCELLED, INTERRUPTED, MISC = range(6)

# Buildrequest results
NO_RESULT, SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(-1, 6)

# Slave status
IDLE = 0
BUSY = 1
UNKNOWN = 2

PLATFORMS_BUILDERNAME = {
    'linux-mock': [
        re.compile('^b2g_((?!(test|talos)).)+$'),
        re.compile('^b2g_.+_linux32_gecko'),
        re.compile('^Linux .+ (build|non-unified|valgrind)$'),
        re.compile('^Android .+ (build|non-unified)$'),
        re.compile('^linux64-.+-haz'),
    ],
    'ubuntu32_vm': [
        re.compile('^Ubuntu VM 12.04 (?!x64).+'),
        re.compile('^b2g_ubuntu32_vm'),
        re.compile('^jetpack-.+-ubuntu32_vm'),
    ],
    'ubuntu64_vm': [
        re.compile('^Ubuntu (Code Coverage )?(ASAN )?VM 12.04 x64 .+'),
        re.compile('^b2g_ubuntu64_vm'),
        re.compile('^b2g_emulator_vm'),
        re.compile('^Android armv7 API 9 .+ test (?!(plain-reftest|crashtest|jsreftest))'),
        re.compile('^Android 2.3 (Armv6 )?Emulator .+ test (?!(plain-reftest|crashtest|jsreftest))'),
        re.compile('^Android 4.3 armv7 API 11\+.*test (?!plain-reftest|crashtest|jsreftest)'),
        re.compile('^jetpack-.+-ubuntu64(-asan)?_vm'),
    ],
    'ubuntu64_emulator_vm': [
        re.compile('^Ubuntu (ASAN )?VM large 12.04 x64 .+'),
        re.compile('^Android armv7 API 9 .+ test (plain-reftest|crashtest|jsreftest)'),
        re.compile('^Android 2.3 (Armv6 )?Emulator .+ test (plain-reftest|crashtest|jsreftest)'),
        re.compile('^Android 4.3 armv7 API 11\+.*debug test .*(?:mochitest)'),
        re.compile('^Android 4.3 armv7 API 11\+.*test (plain-reftest|crashtest|jsreftest)'),
    ],
    'ubuntu32_hw': [
        re.compile('^Ubuntu HW 12.04 (?!x64).+'),
    ],
    'ubuntu64_hw': [
        re.compile('^Android (?:4\.2 )?x86'),
        re.compile('^Ubuntu (ASAN )?HW 12.04 x64'),
    ],
    'snowleopard': [
        re.compile('^Rev4 MacOSX Snow Leopard 10\.6.+'),
        re.compile('^jetpack-.+-snowleopard'),
    ],
    'lion': [
        re.compile('^OS X 10\.7.+'),
        re.compile('^OS X Mulet'),
        re.compile('^b2g_.+_macosx64_gecko'),
        re.compile('^fuzzer-macosx64-lion$'),
    ],
    'mountainlion': [
        re.compile('^Rev5 MacOSX Mountain Lion 10\.8.+'),
        re.compile('^b2g_macosx64 .+ test '),
        re.compile('^jetpack-.+-mountainlion'),
    ],
    'mavericks': [
        re.compile('^Rev5 MacOSX Mavericks 10.9'),
    ],
    'yosemite': [
        re.compile('^Rev5 MacOSX Yosemite 10.10'),
    ],
    'xp-ix': [
        re.compile('^Windows XP 32-bit'),
        re.compile('^jetpack-.+-xp'),
    ],
    'win2k8': [
        re.compile('^WINNT 5\.2 '),
        re.compile('^WINNT 6\.1 '),
        re.compile('^Win32 Mulet'),
        re.compile('^b2g_.+_win32_gecko'),
        re.compile('^fuzzer-win64'),
    ],
    'win7-ix': [
        re.compile('^Windows 7 32-bit '),
        re.compile('^jetpack-.+-win7'),
    ],
    'win8-ix': [
        re.compile('^Windows 8'),
        re.compile('^jetpack-.+-win8'),
        re.compile('^WINNT 6\.2 '),
    ],
    'panda-android': [
        re.compile('^Android 4.0 armv7 API (10|11)'),
        re.compile('^Android 4.0 Panda'),
    ],
}

BUILD_TYPE_BUILDERNAME = {
    'opt': [
        re.compile('.+ opt .+'),
        re.compile('.+(?<!leak test) build'),
        re.compile('.+ talos .+'),          # all talos are made only for opt
        re.compile('.+ nightly$'),          # all nightly builds are opt
        re.compile('.+ xulrunner$'),        # nightly
        re.compile('.+ code coverage$'),    # nightly
    ],
    'debug': [
        re.compile('.+ debug .+'),
        re.compile('.+ leak test build'),
    ],
}

JOB_TYPE_BUILDERNAME = {
    'build': [
        re.compile('.+ build'),
        re.compile('.+(?<!l10n) nightly$'),     # all 'nightly'-s are builds
        re.compile('.+ xulrunner$'),            # nightly
        re.compile('.+ code coverage$'),        # nightly
    ],
    'unittest': [re.compile('.+(?<!leak) test .+')],
    'talos': [re.compile('.+ talos .+')],
    'repack': [re.compile('.+ l10n .+')],
}

SOURCESTAMPS_BRANCH = {
    'l10n-central': [re.compile('^l10n-central.*')],
    'birch': [re.compile('^birch.+'), re.compile('^projects/birch.*')],
    'cedar': [re.compile('^cedar.+'), re.compile('^projects/cedar.*')],
    'electrolysis': [
        re.compile('^electrolysis.*'),
        re.compile('^projects/electrolysis.*')],
    'jaegermonkey': [re.compile('^projects/jaegermonkey.*')],
    'maple': [re.compile('^maple.*'), re.compile('^projects/maple.*')],
    'mozilla-1.9.1': [re.compile('.*mozilla-1\.9\.1.*')],
    'mozilla-1.9.2': [re.compile('.*mozilla-1\.9\.2.*')],
    'mozilla-2.0': [re.compile('.*mozilla-2\.0.*')],
    'mozilla-central': [re.compile('^mozilla-central.*')],
    'places': [re.compile('^places.+'), re.compile('^projects/places.*')],
    'nanojit-central': [re.compile('.*nanojit-central.*')],
    'tracemonkey': [re.compile('^tracemonkey.*')],
    'try': [re.compile('^try$'), re.compile('^tryserver.*')],
}

SLAVE_SILOS = {
    'b-2008-ix': [re.compile('^b-2008-ix-\d+')],
    'bld-lion-r5': [re.compile('^bld-lion-r5-\d+')],
    't-xp32-ix': [re.compile('^t-xp32-ix-\d+')],
    't-w732-ix': [re.compile('^t-w732-ix-\d+')],
    't-w864-ix': [re.compile('^t-w864-ix-\d+')],
    't-snow-r4': [re.compile('^t-snow-r4-\d+')],
    'talos-mtnlion-r5': [re.compile('^talos-mtnlion-r5-\d+')],
    't-yosemite-r5': [re.compile('^t-yosemite-r5-\d+')],
    'bld-linux64-ec2': [re.compile(r'^bld-linux64-ec2-\d+')],
    'bld-linux64-spot': [re.compile(r'^bld-linux64-spot-\d+')],
    'try-linux64-spot': [re.compile(r'^try-linux64-spot-\d+')],
    'tst-linux64-spot': [re.compile(r'^tst-linux64-spot-\d+')],
    'tst-linux32-spot': [re.compile(r'^tst-linux32-spot-\d+')],
    'panda': [re.compile(r'^panda-\d+')],
    'tst-emulator64-spot': [re.compile(r'^tst-emulator64-spot-\d+')],
}

BUILDERS_DETAIL_LEVELS = ['branch', 'platform', 'build_type', 'job_type',
                          'builder']

BUILDSET_REASON = {
    'forcebuild': re.compile("The web-page 'force build' button was pressed by .+"),
    'rebuild': re.compile("The web-page 'rebuild' button was pressed by .+"),
}

# Pushes Report Configs
PUSHES_SOURCESTAMPS_BRANCH_SQL_EXCLUDE = [
    '%unittest',
    '%talos',
    'addontester%',
    '%l10n%',
]


# Wait Times Report Configs

WAITTIMES_BUILDREQUESTS_BUILDERNAME_SQL_EXCLUDE = [
    'fuzzer-%',
    'nanojit-%',
    'release-%',
    'valgrind%',
]

WAITTIMES_BUILDSET_REASON_SQL_EXCLUDE = [
    "The web-page 'force build' button was pressed by %",
    "The web-page 'rebuild' button was pressed by %",
    "%Rebuilt by %",
]

WAITTIMES_BUILDREQUESTS_BUILDERNAME_EXCLUDE = [
    re.compile('.+ l10n .+'),
]

_STATUS_TO_STR = {
    PENDING: 'PENDING',
    RUNNING: 'RUNNING',
    COMPLETE: 'COMPLETE',
    CANCELLED: 'CANCELLED',
    INTERRUPTED: 'INTERRUPTED',
    MISC: 'MISC',
}

_RESULTS_TO_STR = {
    NO_RESULT: '-',
    SUCCESS: 'success',
    WARNINGS: 'warnings',
    FAILURE: 'failure',
    SKIPPED: 'skipped',
    EXCEPTION: 'exception',
    RETRY: 'retry',
}


def status_to_str(status):
    """Return the status as string.

    Input:  status - status int value, one of: PENDING, RUNNING, COMPLETE,
                CANCELLED, INTERRUPTED, MISC
    Output: status string representation
    """
    if status not in _STATUS_TO_STR:
        status = MISC
    return _STATUS_TO_STR[status]


def results_to_str(results):
    """Return the results as string.

    Input:  results - results int value, one of: NO_RESULT, SUCCESS, WARNINGS,
                FAILURE, SKIPPED, EXCEPTION, RETRY
    Output: results string representation
    """
    if results not in _RESULTS_TO_STR:
        results = NO_RESULT
    return _RESULTS_TO_STR[results]


def get_branch_name(text):
    """Returns the branch name.

    Input:  text - field value from schedulerdb table
    Output: branch (one in SOURCESTAMPS_BRANCH keys: mozilla-central,
            mozilla-1.9.1, or text if not found
    """
    if not text:
        return None

    text = text.lower()
    for branch in SOURCESTAMPS_BRANCH:
        for pat in SOURCESTAMPS_BRANCH[branch]:
            if pat.match(text):
                return branch

    return text


def get_platform(buildername):
    """Returns the platform name for a buildername.

    Input:  buildername - buildername field value from buildrequests
                schedulerdb table
    Output: platform (one in PLATFORMS_BUILDERNAME keys: linux, linux64, ...)
    """
    if not buildername:
        return None

    if buildername.startswith('TB '):
        buildername = buildername[3:]

    for platform in PLATFORMS_BUILDERNAME:
        for pat in PLATFORMS_BUILDERNAME[platform]:
            if pat.match(buildername):
                return platform

    return 'other'


def get_build_type(buildername):
    """Returns the build type based on the buildername.

    Build requests are matched to a build type, as following:
    * opt, if buildername contains 'opt', 'build' not preceded by 'leak test',
         'talos' (all talos tests are for opt), 'nightly' or 'xulrunner'
         (last 2 are all nightlies)
    * debug, if buildername contains 'debug' or 'leak test build' (debug build)

    Input:  buildername - buildername field value from buildrequests
                schedulerdb table
    Output: build type (one in BUILD_TYPE_BUILDERNAME keys: opt or debug)
    """
    if not buildername:
        return None

    for build_type in BUILD_TYPE_BUILDERNAME:
        for pat in BUILD_TYPE_BUILDERNAME[build_type]:
            if pat.match(buildername):
                return build_type

    return None


def get_job_type(buildername):
    """Returns the job type based on the buildername.

    Build requests are matched to a job type, as following:
    * build, if buildername contains 'build', 'nightly' or 'xulrunner'
        (last 2 are all nightlies)
    * unittest, if buildername contains 'test', but not preceded by 'leak'
        (it would make it a build)
    * talos, if buildername contains 'talos'

    Input:  buildername - buildername field value from buildrequests
                schedulerdb table
    Output: job type (one in JOB_TYPE_BUILDERNAME keys: build, unittest or talos)
    """
    if not buildername:
        return None

    for job_type in JOB_TYPE_BUILDERNAME:
        for pat in JOB_TYPE_BUILDERNAME[job_type]:
            if pat.match(buildername):
                return job_type

    return None


def get_revision(revision):
    """Returns at most the first 12 characters of the revision number, the
    rest are not signifiant, or None, if revision is None.
    """
    return revision[:12] if revision else revision


def get_silos(slave_name):
    """Returns the silos name based on the slave name."""
    if not slave_name:
        return None

    for silos_name in SLAVE_SILOS:
        for pat in SLAVE_SILOS[silos_name]:
            if pat.match(slave_name):
                return silos_name

    return None


def get_time_interval(starttime, endtime):
    """Returns (sarttime2, endtime2) tuple, where the starttime2 is the exact
    value of input parameter starttime if specified, or endtime minus 24 hours
    if not. endtime2 is the exact value of input parameter endtime if
    specified, or starttime plus 24 hours or current time (if starttime is not
    specified either).

    Input: stattime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
    Output: (stattime2, endtime2)
    """
    nowtime = time.time()
    if not endtime:
        endtime = min(starttime + 24 * 3600 if starttime else nowtime, nowtime)
    if not starttime:
        starttime = endtime - 24 * 3600

    return starttime, endtime
