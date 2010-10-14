"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
# Import helpers as desired, or define your own, ie:
#from webhelpers.html.tags import checkbox, password

from pylons import url
from webhelpers.html import tags
import time, datetime

def strf_hms(tspans):
    h = tspans/3600
    tspans -= h*3600
    m = tspans/60
    s = tspans - m*60
    
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
        start = self._first_sunday_on_or_after(USTimeZone.DSTSTART.replace(year=dt.year))
        end = self._first_sunday_on_or_after(USTimeZone.DSTEND.replace(year=dt.year))

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
    """Convert a time expressed in seconds since the epoch to a string representing Pacific time. 
    If secs is not provided or None, the current time as returned by time() is used.
    """
    if not timestamp: timestamp = time.time()
    dt = datetime.datetime.fromtimestamp(timestamp, pacific_tz)

    return dt.strftime(format)

def convert_master(m):
    """ Given a claimed_by_name from schedulerdb return
         * pretty_name, eg 'buildbot-master1:8011'
         * master_url, eg 'http://buildbot-master1.build.mozilla.org:8011'
    """
    if m in ('talos-master02.build.mozilla.org:/builds/buildbot/tests-master',
             'test-master01.build.mozilla.org:/builds/buildbot/tests-master',
             'test-master02.build.mozilla.org:/builds/buildbot/tests-master',
             'buildbot-master1.build.scl1.mozilla.com:/builds/buildbot/tests_master4/master',
             'buildbot-master2.build.scl1.mozilla.com:/builds/buildbot/tests_master6/master'):
        port = '8012'
    elif m in ('production-master02.build.mozilla.org:/builds/buildbot/try-trunk-master',
               'buildbot-master1.build.scl1.mozilla.com:/builds/buildbot/tests_master3/master',
               'buildbot-master2.build.scl1.mozilla.com:/builds/buildbot/tests_master5/master'):
        port = '8011'
    else:
        port = '8010'

    pretty_name = '%s:%s' % (m.split('.')[0], port)
    master_url = 'http://%s' % pretty_name.replace(':','.build.mozilla.org:')

    return {'pretty_name': pretty_name, 'master_url': master_url}
