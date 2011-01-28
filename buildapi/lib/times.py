"""
Module for handling times.  It's harder than it looks!
"""
import pytz
import calendar
import time
from datetime import datetime, timedelta

oneday = timedelta(days=1)
UTC = pytz.timezone('UTC')

def now(timezone):
    return ts2dt(time.time(), timezone)

def dt2ts(dt):
    """Returns a timestamp (epoch time) from a timezone aware datetime
    instance"""
    assert dt.tzinfo
    return calendar.timegm(dt.utctimetuple())

def ts2dt(ts, timezone):
    """Returns a datetime instance in the given timezone (a pytz timezone
    instance) from a timestamp (epoch time)"""
    date = datetime.utcfromtimestamp(ts)
    date = timezone.normalize(UTC.localize(date).astimezone(timezone))
    return date
