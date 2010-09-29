import simplejson
from sqlalchemy import outerjoin

import buildapi.model.meta as meta
from buildapi.model.util import BUILDSET_REASON, PENDING, RUNNING, COMPLETE, \
CANCELLED, INTERRUPTED, MISC
from buildapi.model.util import NO_RESULT, SUCCESS, WARNINGS, FAILURE, \
SKIPPED, EXCEPTION, RETRY
from buildapi.model.util import get_branch_name, get_platform, get_build_type, \
get_job_type, get_revision, results_to_str, status_to_str

b = meta.scheduler_db_meta.tables['builds']
br = meta.scheduler_db_meta.tables['buildrequests']
bs = meta.scheduler_db_meta.tables['buildsets']
s = meta.scheduler_db_meta.tables['sourcestamps']
sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
c = meta.scheduler_db_meta.tables['changes']

def BuildRequestsQuery():
    """Constructs the sqlalchemy query for fetching all build requests.

    Input: None
    Output: query
    """
    q = outerjoin(br, b, b.c.brid==br.c.id) \
            .join(bs, bs.c.id==br.c.buildsetid) \
            .join(s, s.c.id==bs.c.sourcestampid) \
            .outerjoin(sch, sch.c.sourcestampid==s.c.id) \
            .outerjoin(c, c.c.changeid==sch.c.changeid) \
            .select() \
            .with_only_columns([
                b.c.number,
                br.c.id.label('brid'),
                br.c.buildsetid,
                br.c.buildername, 
                s.c.branch, 
                s.c.id.label('ssid'),
                c.c.when_timestamp,
                br.c.submitted_at,
                br.c.claimed_at,
                b.c.start_time,
                br.c.complete_at,
                b.c.finish_time,
                br.c.claimed_by_name,
                s.c.revision,
                br.c.complete,
                bs.c.reason,
                br.c.results,
                c.c.author,
                c.c.comments,
                c.c.revlink,
                c.c.category,
                c.c.repository,
                c.c.project,
            ])
    q = q.group_by(br.c.id, b.c.id)  # some build request might have multiple builds

    return q

class BuildRequest(object):

    def __init__(self, number=None, brid=None, branch=None, buildername=None,
        revision=None, ssid=None, when_timestamp=None, submitted_at=None,
        claimed_at=None, start_time=None, complete_at=None, finish_time=None,
        claimed_by_name=None, complete=0, reason=None, results=None,
        author=None, comments=None, revlink=None, category=None,
        repository=None, project=None, buildsetid=None):
        self.number = number
        self.brid = brid
        self.branch = branch
        self.branch_name = get_branch_name(branch)
        self.buildername = buildername
        self.ssid = ssid
        self.revision = get_revision(revision)    # get at most the first 12 chars

        self.when_timestamp = when_timestamp
        self.submitted_at = submitted_at
        self.claimed_at = claimed_at
        self.start_time = start_time
        self.complete_at = complete_at
        self.finish_time = finish_time

        self.claimed_by_name = claimed_by_name
        self.complete = complete
        self.reason = reason
        self.results = results if results!=None else NO_RESULT

        self.author = author
        self.comments = comments
        self.revlink = revlink
        self.category = category
        self.repository = repository 
        self.project = project
        self.buildsetid = buildsetid

        self.status = self._compute_status()

        self.platform = get_platform(buildername)
        self.build_type = get_build_type(buildername) # opt / debug
        self.job_type = get_job_type(buildername)     # build / unittest / talos

    def _compute_status(self):
        # when_timestamp & submitted_at ?
        if not self.complete and not self.complete_at and not self.finish_time:  # not complete
            if self.start_time and self.claimed_at:         # running
                return RUNNING
            if not self.start_time and not self.claimed_at: # pending
                return PENDING
        if self.complete and self.complete_at and self.finish_time and \
            self.start_time and self.claimed_at:            # complete
            return COMPLETE
        if not self.start_time and not self.claimed_at and \
            self.complete and self.complete_at and not self.finish_time:  # cancelled
            return CANCELLED
        if self.complete and self.complete_at and not self.finish_time and \
            self.start_time and self.claimed_at:
            # build interrupted (eg slave disconnected) and buildbot retriggered the build
            return INTERRUPTED

        return MISC                       # what's going on?

    def get_duration(self):
        change_time = self.when_timestamp or self.submitted_at
        return self.complete_at - change_time if self.complete_at and change_time else 0

    def get_wait_time(self):
        change_time = self.when_timestamp or self.submitted_at
        return self.start_time - change_time if self.start_time and change_time else 0

    def get_run_time(self):
        return self.get_duration() - self.get_wait_time()

    def to_dict(self, summary=False):
        json_obj = {
            'number': self.number,
            'brid': self.brid,
            'branch': self.branch,
            'branch_name': self.branch_name,
            'buildername': self.buildername,
            'ssid': self.ssid,
            'revision': self.revision,
            'when_timestamp': self.when_timestamp, 
            'submitted_at': self.submitted_at,
            'claimed_at': self.claimed_at,
            'start_time': self.start_time,
            'complete_at': self.complete_at,
            'finish_time': self.finish_time,
            'claimed_by_name': self.claimed_by_name,
            'complete': self.complete,
            'reason': self.reason,
            'results': self.results,
            'results_str': results_to_str(self.results),
            'status': self.status,
            'status_str': status_to_str(self.status),
            'author': self.author,
            'comments': self.comments,
            'revlink': self.revlink,
            'category': self.category,
            'repository': self.repository,
            'project': self.project,
            'buildsetid': self.buildsetid,
        }
        return json_obj

    def jsonify(self, summary=False):
        return simplejson.dumps(self.to_dict(summary=summary))
