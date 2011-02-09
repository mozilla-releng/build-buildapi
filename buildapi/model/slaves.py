from sqlalchemy import join
from datetime import datetime
import re
import time

import buildapi.model.meta as meta
from buildapi.model.reports import Report, IntervalsReport
from buildapi.model.util import get_time_interval, get_silos
from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, \
SKIPPED, EXCEPTION, RETRY, SLAVE_SILOS, BUSY, IDLE


b = meta.status_db_meta.tables['builds']
s = meta.status_db_meta.tables['slaves']
bd = meta.status_db_meta.tables['builders']

def BuildsQuery(starttime=None, endtime=None, slave_id=None, builder_name=None,
    get_builder_name=False):
    """Constructs the sqlalchemy query for fetching all builds from statusdb 
    in the specified time interval, satisfying some contraints.

    Input: starttime - start time, UNIX timestamp (in seconds)
           endtime - end time, UNIX timestamp (in seconds)
           slave_id - slave id, if specified returns only the builds on this 
                slave
           builder_name - builder name, if specified returns only the builds on
                this builder
           get_builder_name - boolean specifying whether or not to get the 
                builder name for each build
    Output: query
    """
    q = join(b, s, b.c.slave_id == s.c.id)
    with_columns = [b.c.slave_id, s.c.name.label('slave_name'), b.c.result,
                    b.c.builder_id, b.c.starttime, b.c.endtime]

    if get_builder_name or builder_name:
        q = q.join(bd, bd.c.id == b.c.builder_id)
        with_columns.append(bd.c.name.label('builder_name'))

    q = q.select().with_only_columns(with_columns)

    if slave_id != None:
        q = q.where(b.c.slave_id == slave_id)
    if builder_name != None:
        q = q.where(bd.c.name == builder_name)
    if starttime:
        q = q.where(b.c.starttime >= starttime)
    if endtime:
        q = q.where(b.c.starttime <= endtime)

    return q

def GetSlavesReport(starttime=None, endtime=None, int_size=0, last_int_size=0):
    """Get the slaves report for the speficied time interval.

    Input: starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
           last_int_size - the length in seconds for the last time interval 
                for which to compute fail and busy/idle percentage.
    Output: SlavesReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    starttime_date = datetime.fromtimestamp(starttime)
    endtime_date = datetime.fromtimestamp(endtime)

    report = SlavesReport(starttime, endtime, int_size=int_size,
        last_int_size=last_int_size)

    q = BuildsQuery(starttime=starttime_date, endtime=endtime_date)
    q_results = q.execute()

    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        build = Build(**params)
        report.add(build)

    return report

def GetSlaveDetailsReport(slave_id=None, starttime=None, endtime=None,
    int_size=0, last_int_size=0):
    """Get the slave details report for a slave in the speficied time interval.

    Input: slave_id - slave id
           starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
           int_size - break down results per interval (in seconds), if specified
           last_int_size - the length in seconds for the last time interval 
                for which to compute fail and busy/idle percentage.
    Output: SlaveDetailsReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    starttime_date = datetime.fromtimestamp(starttime)
    endtime_date = datetime.fromtimestamp(endtime)

    report = SlaveDetailsReport(starttime, endtime, slave_id, 
        int_size=int_size, last_int_size=last_int_size)

    q = BuildsQuery(slave_id=slave_id, get_builder_name=True,
        starttime=starttime_date, endtime=endtime_date)
    q_results = q.execute()

    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        build = Build(**params)
        report.add(build)
        if not report.name:
            report.name = build.slave_name

    return report

def GetStatusBuildersReport(starttime=None, endtime=None):
    """Get the builders report based on statusdb for the speficied time 
    interval.

    Input: starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
    Output: BuildersReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    starttime_date = datetime.fromtimestamp(starttime)
    endtime_date = datetime.fromtimestamp(endtime)

    report = BuildersReport(starttime, endtime)

    q = BuildsQuery(starttime=starttime_date, endtime=endtime_date,
        get_builder_name=True)
    q_results = q.execute()

    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        build = Build(**params)
        report.add(build)

    return report

def GetBuilderDetailsReport(builder_name=None, starttime=None, endtime=None):
    """Get the builder details report based on statusdb for a builder in the 
    speficied time interval.

    Input: builder_name - builder name
           starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
    Output: BuilderDetailsReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)
    starttime_date = datetime.fromtimestamp(starttime)
    endtime_date = datetime.fromtimestamp(endtime)

    report = BuilderDetailsReport(starttime, endtime, name=builder_name)

    q = BuildsQuery(builder_name=builder_name, get_builder_name=True,
        starttime=starttime_date, endtime=endtime_date)
    q_results = q.execute()

    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        build = Build(**params)
        report.add(build)

    return report

class SlavesReport(IntervalsReport):
    """Contains a summary Slave Report for each slave that had at least one 
    build within the specified timeframe.
    """
    outdated = -1

    def __init__(self, starttime, endtime, int_size=0, last_int_size=0):
        IntervalsReport.__init__(self, starttime, endtime, int_size=int_size)

        self.last_int_size = last_int_size
        self.slaves = {}

        self._busy = 0
        self._avg_busy = 0

        # outdated flags
        self._num_busy = SlavesReport.outdated
        self._avg_busy_time = SlavesReport.outdated

        self.silos = sorted(SLAVE_SILOS.keys())

    def add(self, build):
        """Update the report by adding a build to the corresponding Slave 
        Report.
        """
        slave_id = build.slave_id
        if slave_id not in self.slaves:
            self.slaves[slave_id] = SlaveDetailsReport(self.starttime, 
                self.endtime, slave_id, name=build.slave_name, 
                last_int_size=self.last_int_size, summary=True)

        self.slaves[slave_id].add(build)

        self._num_busy = SlavesReport.outdated
        self._avg_busy_time = SlavesReport.outdated

    def total_slaves(self):
        """Total number of slaves."""
        return len(self.slaves.keys())

    def endtime_total_busy(self):
        """Total number of busy slaves at endtime."""
        if self._num_busy == SlavesReport.outdated:
            self._num_busy = 0
            for slave in self.slaves.values():
                if slave.endtime_status() == BUSY:
                    self._num_busy += 1

        return self._num_busy

    def endtime_total_idle(self):
        """Total number of idle slaves at endtime."""
        return self.total_slaves() - self.endtime_total_busy()

    def get_int_busy(self):
        """Number of busy machines per each interval."""
        int_busy = [ 0 ] * self.int_no

        for slave_id in self.slaves:
            slave = self.slaves[slave_id]
            disc_intervals = set()

            intervals = sorted(slave.busy)
            intervals.append((self.endtime, None, None)) # append fake interval
            for inter in xrange(len(intervals) - 1):
                start, end, _ = intervals[inter]
                next_inter_start = intervals[inter + 1][0]
                end = min(end or (next_inter_start - 1), self.endtime - 1)

                start_idx = self.get_interval_index(start)
                end_idx = self.get_interval_index(end)
                disc_intervals.update(xrange(start_idx, end_idx))

            for int_idx in disc_intervals:
                int_busy[int_idx] += 1

        return int_busy

    def get_int_busy_silos(self):
        """Number of busy machines per each interval and per silos."""
        total_slaves = {}
        int_busy = { 'Totals': [ 0 ] * self.int_no }
        for silos_name in SLAVE_SILOS:
            int_busy[silos_name] = [ 0 ] * self.int_no
            total_slaves[silos_name] = set()

        for slave_id in self.slaves:
            slave = self.slaves[slave_id]
            silos_name = get_silos(slave.name)

            disc_intervals = set()

            intervals = sorted(slave.busy)
            intervals.append((self.endtime, None, None)) # append fake interval
            for inter in xrange(len(intervals) - 1):
                start, end, _ = intervals[inter]
                next_inter_start = intervals[inter + 1][0]
                end = min(end or (next_inter_start - 1), self.endtime - 1)

                start_idx = self.get_interval_index(start)
                end_idx = self.get_interval_index(end)
                disc_intervals.update(xrange(start_idx, end_idx))

            for int_idx in disc_intervals:
                int_busy[silos_name][int_idx] += 1
                int_busy['Totals'][int_idx] += 1

            total_slaves[silos_name].add(slave.name)

        totals = dict([(silos_name, len(total_slaves[silos_name])) 
            for silos_name in total_slaves])
        totals['Totals'] = self.total_slaves()

        return int_busy, totals

    def get_avg_busy(self):
        """Average across all slaves of slave busy time percentage."""
        if self._avg_busy_time == SlavesReport.outdated:
            busy_sum = 0
            total = self.total_slaves()
            for slave in self.slaves.values():
                busy_sum += slave.get_ptg_busy()

            self._avg_busy_time = busy_sum / total if total else 0

        return self._avg_busy_time

    def to_dict(self, summary=False):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'last_int_size': self.last_int_size,
            'slaves': [],
        }
        for slave_id in self.slaves:
            slave_obj = self.slaves[slave_id].to_dict(summary=True)
            json_obj['slaves'].append(slave_obj)

        return json_obj

class SlaveDetailsReport(IntervalsReport):

    def __init__(self, starttime, endtime, slave_id, name=None, int_size=0, 
        last_int_size=0, summary=False):
        IntervalsReport.__init__(self, starttime, endtime, int_size=int_size)

        self.slave_id = slave_id
        self.name = name
        self.last_int_size = last_int_size

        self.summary = summary

        # builds, only when summary=False
        self.builds = []
        self.last_build = None

        self._d_sum = 0     # sum of all durations
        self.busy = []      # busy intervals

        # results
        self.total = 0
        self.results = {
            NO_RESULT: 0,
            SUCCESS: 0,
            WARNINGS: 0,
            FAILURE: 0,
            SKIPPED: 0,
            EXCEPTION: 0,
            RETRY: 0,
        }

        self.timeframe = self.endtime - self.starttime \
            if self.starttime and self.endtime else 0

        self.int_total = [0] * self.int_no
        self.results_int = {
            SUCCESS: [0] * self.int_no,
            WARNINGS: [0] * self.int_no,
            FAILURE: [0] * self.int_no,
        }

        # last interval
        self.last_int_sum = 0
        self.last_int_total = 0
        self.last_int_fail = 0

    def add(self, build):
        """Update the slave report by analyzing a build's properties."""
        self.total += 1

        # results
        result = build.result if build.result != None else NO_RESULT
        if result in self.results:
            self.results[result] += 1

        # results per interval
        int_idx = self.get_interval_index(build.starttime)
        self.int_total[int_idx] += 1
        if result in (FAILURE, SKIPPED, EXCEPTION, RETRY, NO_RESULT):
            result = FAILURE
        self.results_int[result][int_idx] += 1

        # sum durations
        self._d_sum += self._busy_time(build)

        if build.starttime:
            endtime = build.endtime if (build.endtime and 
                build.endtime > build.starttime) else None
            self.busy.append((build.starttime, endtime, result))

        # last interval
        if build.starttime and self.endtime and self.last_int_size and (
            build.starttime >= self.endtime - self.last_int_size):
            self.last_int_sum += self._busy_time(build)
            self.last_int_total += 1

            if result in (FAILURE, SKIPPED, EXCEPTION, RETRY, NO_RESULT):
                self.last_int_fail += 1

        # status at endtime
        if not self.last_build or (self.last_build and build.starttime and 
            build.starttime >= self.last_build.starttime):
            self.last_build = build

        if not self.summary:
            self.builds.append(build)

    def _busy_time(self, build):
        """Build run time within the report's timeframe."""
        if build.duration:
            return (min(build.endtime, self.endtime) -
                    max(build.starttime, self.starttime))
        return 0

    def endtime_status(self):
        """Slave status at endtime: BUSY or IDLE."""
        if self.last_build and (not self.last_build.endtime or 
            self.last_build.endtime > self.endtime):
            return BUSY
        return IDLE

    def get_avg_duration(self):
        """The average (mean) duration of the builds which run on this slave."""
        return int(float(self._d_sum) / self.total) if self.total else 0

    def get_results_fail_all(self):
        """The number of all failing builds (the sum of FAILURE, SKIPPED, 
        EXCEPTION, RETRY, NO_RESULT).
        """
        return sum([self.results[result] for result in 
            (FAILURE, SKIPPED, EXCEPTION, RETRY, NO_RESULT)])

    def get_ptg_results(self):
        """The results (SUCCESS, WARNINGS, etc. builds) as percentage."""
        if self.total == 0:
            return dict([(result, 0) for result in self.results])
        return dict([(result, n * 100. / self.total) for (result, n) in 
            self.results.items()])

    def get_ptg_int_results(self):
        """The results (SUCCESS, WARNINGS, etc. builds) as percentage per each 
        time interval (if int_size>0).
        """
        r = { 
            SUCCESS: [0] * self.int_no,
            WARNINGS: [0] * self.int_no,
            FAILURE: [0] * self.int_no,
        }
        for i in xrange(self.int_no):
            total = self.int_total[i]
            for result in self.results_int.keys():
                n = self.results_int[result][i]
                r[result][i] = n * 100. / total if total else 0

        return r

    def get_last_int_ptg_fail(self):
        """The percentage of all failing builds within the last interval size.
        """
        return self.last_int_fail * 100. / self.last_int_total \
            if self.last_int_total else 0

    def get_ptg_busy(self):
        """The percentage of slave busy time."""
        return self._d_sum * 100. / self.timeframe if self.timeframe else -1

    def get_last_int_ptg_busy(self):
        """The percentage of slave busy time within the last interval size."""
        return self.last_int_sum * 100. / self.last_int_size \
            if self.last_int_size else 0

    def to_dict(self, summary=False):
        json_obj = {
            'slave_id': self.slave_id,
            'name': self.name,
            'starttime': self.starttime,
            'endtime': self.endtime,
            'busy': self.get_ptg_busy(),
            'busy_last_int_size': self.get_last_int_ptg_busy(),
            'avg_build_duration': self.get_avg_duration(),
            'total': self.total,
            'results_success': self.results[SUCCESS],
            'results_warnings': self.results[WARNINGS],
            'results_failure_all': self.get_results_fail_all(),
            'results_failure': self.results[FAILURE],
            'results_skipped': self.results[SKIPPED],
            'results_exception': self.results[EXCEPTION],
            'results_retry': self.results[RETRY],
            'int_size': self.int_size,
            'last_int_size': self.last_int_size,
        }

        if not summary:
            json_obj['builds'] = []
            for build in self.builds:
                json_obj['builds'].append(build.to_dict(summary=True))

        return json_obj

class BuildersReport(Report):
    """Contains a summary Builder Report for each builder that had at least 
    one build within the specified timeframe.
    """

    def __init__(self, starttime, endtime):
        Report.__init__(self)

        self.starttime = starttime
        self.endtime = endtime
        self.builders = {}

    def add(self, build):
        """Update the report by adding a build to the corresponding Builder 
        Report.
        """
        builder_name = build.builder_name
        if builder_name not in self.builders:
            self.builders[builder_name] = BuilderDetailsReport(self.starttime, 
                self.endtime, name=builder_name, summary=True)

        self.builders[builder_name].add(build)

    def to_dict(self, summary=False):
        json_obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'builders': [],
        }
        for builder in self.builders:
            json_obj['builders'].append(builder.to_dict(summary=True))

        return json_obj

class BuilderDetailsReport(Report):

    def __init__(self, starttime, endtime, name=None, summary=False):
        Report.__init__(self)

        self.name = name
        self.starttime = starttime
        self.endtime = endtime
        self.summary = summary

        self.slaves = {}

        # sum of all durations
        self._d_sum = 0
        # results
        self.total = 0
        self.results = {
            NO_RESULT: 0,
            SUCCESS: 0,
            WARNINGS: 0,
            FAILURE: 0,
            SKIPPED: 0,
            EXCEPTION: 0,
            RETRY: 0,
        }

    def add(self, build):
        """Update the builder report by analyzing a build's properties."""
        self.total += 1

        # results
        result = build.result if build.result != None else NO_RESULT
        if result in self.results:
            self.results[result] += 1

        # sum durations
        self._d_sum += build.duration

        # report per slave
        slave_id = build.slave_id
        if slave_id not in self.slaves:
            self.slaves[slave_id] = SlaveDetailsReport(self.starttime, 
                self.endtime, slave_id, name=build.slave_name, summary=True)
        if not self.summary:
            self.slaves[slave_id].add(build)

    def get_avg_duration(self):
        """The average (mean) duration of the builds which run on this slave."""
        return int(float(self._d_sum) / self.total) if self.total else 0

    def get_results_fail_all(self):
        """The number of all failing builds (the sum of FAILURE, SKIPPED, 
        EXCEPTION, RETRY, NO_RESULT).
        """
        return sum([self.results[result] for result in 
            (FAILURE, SKIPPED, EXCEPTION, RETRY, NO_RESULT)])

    def get_ptg_results(self):
        """The results (SUCCESS, WARNINGS, etc. builds) as percentage."""
        if self.total == 0:
            return dict([(result, 0) for result in self.results])
        return dict([(result, n * 100. / self.total) 
            for (result, n) in self.results.items()])

    def to_dict(self, summary=False):
        json_obj = {
            'name': self.name,
            'starttime': self.starttime,
            'endtime': self.endtime,
            'avg_build_duration': self.get_avg_duration(),
            'total': self.total,
            'results_success': self.results[SUCCESS],
            'results_warnings': self.results[WARNINGS],
            'results_failure_all': self.get_results_fail_all(),
            'results_failure': self.results[FAILURE],
            'results_skipped': self.results[SKIPPED],
            'results_exception': self.results[EXCEPTION],
            'results_retry': self.results[RETRY],
        }

        if not summary:
            json_obj['slaves'] = []
            for slave_id in self.slaves:
                slave_obj = self.slaves[slave_id].to_dict(summary=True)
                json_obj['slaves'].append(slave_obj)

        return json_obj

class Build(object):
    def __init__(self, slave_id=None, slave_name=None, result=None, 
        builder_id=None, builder_name=None, starttime=None, endtime=None):
        self.slave_id = slave_id
        self.slave_name = slave_name
        self.result = result
        self.builder_id = builder_id
        self.builder_name = builder_name

        self.starttime = time.mktime(starttime.timetuple()) \
            if starttime else None
        self.endtime = time.mktime(endtime.timetuple()) if endtime else None

        # some endtimes are like 1970-01-01 00:00:01
        self.duration = max(0, self.endtime - self.starttime
            if self.starttime and self.endtime else 0)

    def to_dict(self):
        json_obj = {
            'slave_id': self.slave_id,
            'slave_name': self.slave_name,
            'builder_id': self.builder_id,
            'starttime': self.starttime if self.starttime else 0,
            'endtime': self.endtime if self.endtime else 0,
            'duration': self.duration,
            'result': self.result,
        }

        return json_obj
