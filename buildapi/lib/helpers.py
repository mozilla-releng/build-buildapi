"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
import time, datetime
import logging
import urllib
import urllib2

from pylons import url, app_globals
from webhelpers.html import tags

from pylons.decorators.cache import beaker_cache

import buildapi.model.builds
from buildapi.lib import json
from buildapi.model.util import BUILDPOOL, TRYBUILDPOOL, TESTPOOL, SUCCESS, RETRY

log = logging.getLogger(__name__)

def strf_YmdhMs(secs):
    y = secs / 31536000
    secs -= y * 31536000
    m = secs / 2592000
    secs -= m * 2592000
    d = secs / 86400
    secs -= d * 86400
    return ("%dy, %dm, %dd " % (y, m, d)) + strf_hms(secs)

def strf_hms(tspans):
    h = tspans // 3600
    tspans -= h * 3600
    m = tspans // 60
    s = tspans - m * 60

    return "%dh %dm %ds" % (h, m, s)

ZERO = datetime.timedelta(0)
HOUR = datetime.timedelta(hours=1)

class USTimeZone(datetime.tzinfo):
    # In the US, DST starts at 2am (standard time) on the first Sunday in April.
    DSTSTART = datetime.datetime(1, 4, 1, 2)
    # and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
    # which is the first Sunday on or after Oct 25.
    DSTEND = datetime.datetime(1, 10, 25, 1)

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = datetime.timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = self._first_sunday_on_or_after(
            USTimeZone.DSTSTART.replace(year=dt.year))
        end = self._first_sunday_on_or_after(
            USTimeZone.DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

    def _first_sunday_on_or_after(self, dt):
        days_to_go = 6 - dt.weekday()
        if days_to_go:
            dt += datetime.timedelta(days_to_go)
        return dt

class Pacific(USTimeZone):
    def __init__(self):
        USTimeZone.__init__(self, -8, "Pacific",  "PST", "PDT")

pacific_tz = Pacific()
time_format = '%a, %d %b %Y %H:%M:%S %z (%Z)'

def pacific_time(timestamp, format=time_format):
    """Convert a time expressed in seconds since the epoch to a string
    representing Pacific time. If secs is not provided or None, the current
    time as returned by time() is used.
    """
    if not timestamp:
        timestamp = time.time()
    dt = datetime.datetime.fromtimestamp(timestamp, pacific_tz)

    return dt.strftime(format)


# Matches a master from production-masters.json, to the corresponding
# build pool, by looking at the 'role' field
ROLE_MASTERS_POOLS = {
    'build': BUILDPOOL,
    'tests': TESTPOOL,
    'try': TRYBUILDPOOL,
}

_masters = []
_masters_by_dbname = {}
_masters_pools = {BUILDPOOL: [], TRYBUILDPOOL: [], TESTPOOL: []}
_last_master_check = 0
# Cache for 5 minutes
_masters_cache_timeout = 300
def get_masters():
    global _masters, _last_master_check, _masters_by_dbname, _masters_pools

    now = time.time()

    if now - _last_master_check < _masters_cache_timeout:
        return _masters

    masters_url = app_globals.masters_url
    log.info("Fetching master list from %s", masters_url)
    try:
        masters = json.load(urllib2.urlopen(masters_url, timeout=30))
        _masters = masters
    except:
        log.exception("Error loading masters json; using old list")
        return _masters

    _last_master_check = now
    _masters_by_dbname = {}
    _masters_pools = {BUILDPOOL: [], TRYBUILDPOOL: [], TESTPOOL: []}
    for m in _masters:
        _masters_by_dbname[m['db_name']] = m
        pool = ROLE_MASTERS_POOLS.get(m['role'], None)
        if pool in _masters_pools:
            _masters_pools[pool].append(m['db_name'])
    return _masters

_branches = {}
_last_branches_check = 0
# Cache for 5 minutes
_last_branches_timeout = 300
def get_branches():
    global _branches, _last_branches_check

    now = time.time()
    if now - _last_branches_check < _last_branches_timeout:
        return _branches

    branches_url = app_globals.branches_url
    log.info("Fetching branches list from %s", branches_url)
    try:
        if branches_url.startswith('TEST:'):
            branches = json.load(open(branches_url.split(':')[1]))
        else:
            branches = json.load(urllib2.urlopen(branches_url, timeout=30))
        _branches = branches
        _last_branches_check = now
    except:
        log.exception("Error loading branches json; using old list")

    return _branches

def get_completeness(job_items, stableDelay):
    now = int(time.time())
    job_info = {'stableDelay': stableDelay,
                'job_complete': False,
                'job_passed': False}

    try:
        unfinished_jobs = [job for job in job_items if (job.get('endtime') is None)
                            or (now - job.get('endtime') < stableDelay)]

        if not unfinished_jobs and job_items != []:    # If list is empty
            job_info['job_complete'] = True
            # RETRY isn't a failure because we're rerunning the job
            failed_jobs = [job for job in job_items if job.get('status') not in (SUCCESS, RETRY)]
            job_info['job_passed'] = len(failed_jobs) == 0
    except TypeError:
        pass
    return job_info

def get_masters_for_pool(pool):
    """Returns the masters for a pool."""
    get_masters()
    return _masters_pools[pool]

def addr_for_master(claimed_by_name):
    """Returns the fully qualified domain name and port for the master
    indicated by claimed_by_name"""
    get_masters()
    if claimed_by_name not in _masters_by_dbname:
        return None, None
    fqdn = _masters_by_dbname[claimed_by_name]['hostname']
    port = _masters_by_dbname[claimed_by_name]['http_port']

    return fqdn, port

def url_for_build(master_addr, buildername, buildnumber):
    fqdn, port = master_addr
    buildername = urllib.quote(buildername, "")
    url = "http://%(fqdn)s:%(port)i/builders/%(buildername)s/builds/%(buildnumber)s" % locals()
    return url

def convert_master(m):
    """ Given a claimed_by_name from schedulerdb return
         * pretty_name, eg 'buildbot-master1:8011'
         * master_url, eg 'http://buildbot-master1.build.mozilla.org:8011'
    """
    fqdn, port = addr_for_master(m)
    if fqdn is None:
        return None
    pretty_name = '%s:%i' % (fqdn.split(".")[0], port)
    master_url = 'http://%(fqdn)s:%(port)i' % locals()

    return {'pretty_name': pretty_name, 'master_url': master_url, 'master_addr': (fqdn, port)}

@beaker_cache(expire=600, cache_response=False)
def get_builders(branch, starttime=None, endtime=None):
    return buildapi.model.builds.getBuilders(branch)
