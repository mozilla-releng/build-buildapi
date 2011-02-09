from buildapi.model.buildrequest import BuildRequest, BuildRequestsQuery
from buildapi.model.endtoend import BuildRun, EndtoEndTimesReport
from buildapi.model.util import get_time_interval

def TryChooserGetEndtoEndTimes(starttime=None, endtime=None, 
    branch_name='mozilla-central'):
    """Get end to end times report for the speficied time interval and branch.

    Input: starttime - start time (UNIX timestamp in seconds), if not 
                specified, endtime minus 24 hours
           endtime - end time (UNIX timestamp in seconds), if not specified, 
                starttime plus 24 hours or current time (if starttime is not 
                specified either)
           branch_name - branch name, default vaue is 'mozilla-central'
    Output: EndtoEndTimesReport
    """
    starttime, endtime = get_time_interval(starttime, endtime)

    q = BuildRequestsQuery(starttime=starttime, endtime=endtime, 
            branch_name=branch_name)
    q_results = q.execute()

    report = TryChooserEndtoEndTimesReport(starttime, endtime, branch_name)
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        br = BuildRequest(**params)
        report.add_build_request(br)

    return report

class TryChooserEndtoEndTimesReport(EndtoEndTimesReport):
    uptodate = -2

    def __init__(self, starttime, endtime, branch_name):
        EndtoEndTimesReport.__init__(self, starttime, endtime, branch_name)
        self.used_trychooser = set()
        self.not_used_trychooser = set()
        self.runs_used_trychooser = 0
        self._trychooser_flag = TryChooserEndtoEndTimesReport.uptodate

    def add_build_request(self, br):
        if br.revision not in self._runs: 
            self._runs[br.revision] = \
                TryChooserBuildRun(br.revision, br.branch_name)
        self._runs[br.revision].add(br)

        self._total_br = EndtoEndTimesReport.outdated
        self._u_total_br = EndtoEndTimesReport.outdated
        self._avg_run_duration = EndtoEndTimesReport.outdated
        self._trychooser_flag = EndtoEndTimesReport.outdated

    def get_used_trychooser(self):
        self._update_trychooser()
        return self.used_trychooser

    def get_not_used_trychooser(self):
        self._update_trychooser()
        return self.not_used_trychooser

    def get_never_used_trychooser(self):
        self._update_trychooser()
        return self.not_used_trychooser - self.used_trychooser

    def get_runs_used_trychooser(self):
        self._update_trychooser()
        return self.runs_used_trychooser

    def _update_trychooser(self, force=False):
        if force or self._trychooser_flag == EndtoEndTimesReport.outdated:
            self.runs_used_trychooser = 0
            for rev in self._runs:
                run = self._runs[rev]
                if run.get_used_trychooser():
                    self.runs_used_trychooser += 1
                for author in run.uses_try_chooser:
                    if run.uses_try_chooser[author]:
                        self.used_trychooser.add(author)
                    else:
                        self.not_used_trychooser.add(author)
        self._trychooser_flag = TryChooserEndtoEndTimesReport.uptodate

class TryChooserBuildRun(BuildRun):

    def __init__(self, revision, branch_name):
        BuildRun.__init__(self, revision, branch_name)
        self.uses_try_chooser = {}  # author: boolean (uses try)
        self.used_trychooser = False

    def add(self, br):
        BuildRun.add(self, br)

        if br.author and br.author not in ('sendchange', 'sendchange-unittest'):
            if br.author not in self.uses_try_chooser:
                self.uses_try_chooser[br.author] = False
            if 'try:' in br.comments:
                self.used_trychooser = True
                self.uses_try_chooser[br.author] = True

    def get_used_trychooser(self):
        return self.used_trychooser

    def to_dict(self, summary=False):
        json_obj = BuildRun.to_dict(self, summary=summary)
        json_obj.update({
            'uses_try_chooser': self.uses_try_chooser,  # the authors
            'used_trychooser': self.used_trychooser,    # true / false
        })

        return json_obj
