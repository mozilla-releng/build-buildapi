import time

from buildapi.model.builds import getBuildsQuery, requestFromRow, buildFromRow, \
        getRevision, getPendingQuery
from buildapi.lib.times import dt2ts, ts2dt, oneday, now

import logging
log = logging.getLogger(__name__)

def getBuilds(branch, starttime, endtime):
    log.info("Getting builds on %s between %s and %s", branch, starttime,
            endtime)
    build_q = getBuildsQuery(branch, starttime, endtime)

    # Elements with the same claimed_by_name, claimed_by_incarnation,
    # claimed_at, buildername, and number are actually the same build and
    # should only be represented once
    builds = {}
    retval = []
    for build in build_q.execute():
        key = (build.claimed_by_name, build.claimed_by_incarnation,
                build.claimed_at, build.buildername, build.number)
        if key in builds:
            request = requestFromRow(build)
            builds[key]['requests'].append(request)
        else:
            builds[key] = buildFromRow(build)
            retval.append(builds[key])

    q = getPendingQuery(branch, starttime, endtime)
    for req in q.execute():
        retval.append(requestFromRow(req))

    return retval

class BuildapiCache:
    def __init__(self, cache, timezone):
        self.cache = cache
        self.timezone = timezone

    def build_key_for_day(self, date, branch):
        assert date.tzinfo
        return "builds:%s:%s" % (branch, date.strftime('%Y-%m-%d'))

    def build_key_for_rev(self, branch, rev):
        return "builds:%s:%s" % (branch, rev)

    def get_builds_for_revision(self, branch, revision):
        revision = revision[:12]
        key = self.build_key_for_rev(branch, revision)
        return self.cache.get(key, getRevision, (branch, revision),
                expire=time.time()+120)

    def get_builds_for_day(self, date, branch):
        """
        Returns a list of builds for the given date (a datetime.datetime instance)
        """
        assert date.tzinfo
        key = self.build_key_for_day(date, branch)
        starttime = dt2ts(date)
        endtime = dt2ts(date + oneday)

        if date - now(self.timezone) < 3*oneday:
            # Expire soon
            expire = time.time() + 60
        else:
            # Don't expire
            expire = 0

        return self.cache.get(key, getBuilds, (branch, starttime, endtime),
                expire=expire)

    def get_builds_for_date_range(self, starttime, endtime, branch, method=0):
        """
        Returns a list of builds for the given date range. starttime and
        endtime should be datetime.datetime instances.
        """
        assert starttime.tzinfo
        assert endtime.tzinfo

        # Naive version: grab every day individually
        if method == 0:
            retval = []
            d = starttime
            while d < endtime:
                builds = self.get_builds_for_day(d, branch)
                retval.extend(builds)
                d += oneday
            return retval

        # Less naive version? grab the entire date range if anything isn't
        # cached
        if method == 1:
            d = starttime
            need_more = False
            while d < endtime:
                key = self.build_key_for_day(d, branch)
                if not self.cache.has_key(key):
                    need_more = True
                    break
                d += oneday

            if not need_more:
                # Fall back to method 0
                return self.get_builds_for_date_range(starttime, endtime,
                        branch, method=0)

            # Do a big query to get everything
            builds = getBuilds(branch,
                    dt2ts(starttime),
                    dt2ts(endtime),
                    )
            retval = builds

            # And then cache the results by date
            days = {}
            for b in builds:
                date = ts2dt(b['starttime'], self.timezone)
                date = date.replace(hour=0, minute=0, second=0, microsecond=0)

                days.setdefault(date, []).append(b)

            for date, builds in days.iteritems():
                if date - now(self.timezone) < 3*oneday:
                    # Expire soon
                    expire = time.time() + 60
                else:
                    # Expire in half an hour
                    expire = time.time() + 1800
                key = self.build_key_for_day(date, branch)
                self.cache.put(key, builds, expire=expire)

            return retval

