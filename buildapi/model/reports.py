import simplejson

class Report(object):
    """Basic Report Class."""

    def to_dict(self, summary=False):
        """Create a POPO representation of the report."""
        return {}

    def jsonify(self, summary=False):
        """Returns the JSON representation of the report."""
        return simplejson.dumps(self.to_dict(summary=summary))

class IntervalsReport(Report):
    """Reports that have a starttime, endtime and some kind of statistics on 
    time intervals (int_size - interval size in seconds).
    """

    def __init__(self, starttime, endtime, int_size=0):
        Report.__init__(self)

        self.starttime = starttime
        self.endtime = endtime
        self.int_size = int_size

        # number of intervals
        self.int_no = int((endtime - starttime - 1) / int_size) + 1 \
            if int_size else 1

    def get_interval_timestamp(self, int_idx):
        """Returns the timestamp of a certain interval, based on its index."""
        return int(self.starttime + int_idx * self.int_size)

    def get_interval_index(self, stime):
        """Returns the index of a certain interval, based on its timestamp."""
        tdiff = stime - self.starttime if stime > self.starttime else 0
        return int(tdiff / self.int_size) if self.int_size else 0
