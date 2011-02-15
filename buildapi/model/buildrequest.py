from sqlalchemy import outerjoin, or_

import buildapi.model.meta as meta
from buildapi.model.util import PENDING, RUNNING, COMPLETE, CANCELLED, \
INTERRUPTED, MISC
from buildapi.model.util import NO_RESULT
from buildapi.model.util import get_branch_name, get_platform, get_build_type, \
get_job_type, get_revision, results_to_str, status_to_str

b = meta.scheduler_db_meta.tables['builds']
br = meta.scheduler_db_meta.tables['buildrequests']
bs = meta.scheduler_db_meta.tables['buildsets']
s = meta.scheduler_db_meta.tables['sourcestamps']
sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
c = meta.scheduler_db_meta.tables['changes']

def BuildRequestsQuery(revision=None, branch_name=None, starttime=None, 
    endtime=None, changeid_all=False):
    """Constructs the sqlalchemy query for fetching build requests.

    It can return multiple rows for one build request, one for each build (if 
    the build request has multiple builds) and one for each changeid (if there 
    are multiple changes for one build request), if an only if changeid_all is 
    True. If changeid_all if False, only one changeid will be returned per 
    build request.

    You should use function GetBuildRequests, which groups all rows into 
    appropiate build request POPOs, and returns them as a dictionary.

    Input: (if any of the parameters are not specified (None), no restrictions
           will be applied for them):
           revision - sourcestamp revision, or list of revisions
           branch_name - branch name
           starttime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
           changeid_all - if True, the query will return 1 row per changeid, 
                thus multiple rows for one build request; 
                if False (the default value), only one row will be returned 
                per build request, with only one of the changeids at random
    Output: query
    """
    q = outerjoin(br, b, b.c.brid == br.c.id).join(
            bs, bs.c.id == br.c.buildsetid).join(
            s, s.c.id == bs.c.sourcestampid).outerjoin(
            sch, sch.c.sourcestampid == s.c.id).outerjoin(
            c, c.c.changeid == sch.c.changeid
        ).select().with_only_columns([
            b.c.id.label('bid'),
            b.c.finish_time,
            b.c.number,
            b.c.start_time,
            br.c.id.label('brid'),
            br.c.buildsetid,
            br.c.buildername,
            br.c.claimed_at,
            br.c.claimed_by_name,
            br.c.complete,
            br.c.complete_at,
            br.c.results,
            br.c.submitted_at,
            bs.c.reason,
            c.c.author,
            c.c.category,
            c.c.changeid,
            c.c.comments,
            c.c.project,
            c.c.repository,
            c.c.revision.label('changes_revision'),
            c.c.revlink,
            c.c.when_timestamp,
            s.c.branch,
            s.c.revision,
            s.c.id.label('ssid'),
        ])

    if revision:
        if not isinstance(revision, list):
            revision = [revision]
        revmatcher = [s.c.revision.like(rev + '%') for rev in revision if rev]
        if revmatcher: 
            q = q.where(or_(*revmatcher))
    if branch_name:
        q = q.where(s.c.branch.like(branch_name + '%'))
    if starttime:
        q = q.where(or_(c.c.when_timestamp >= starttime, 
            br.c.submitted_at >= starttime))
    if endtime:
        q = q.where(or_(c.c.when_timestamp < endtime, 
            br.c.submitted_at < endtime))

    # some build requests might have multiple builds or changeids
    if not changeid_all:
        q = q.group_by(br.c.id, b.c.id)
    # else:
    #     q = q.group_by(br.c.id, b.c.id, c.c.changeid)

    return q

def GetBuildRequests(revision=None, branch_name=None, starttime=None, 
    endtime=None, changeid_all=False):
    """Fetches all build requests matching the parameters, and returns them as 
    a dictionary of build request POPOs, keyed by (br.brid, br.bid) - (build 
    request id, build id). There will be one object per build (so if one build 
    request has multiple builds, there will be more than one object).

    Each build request object will contain the changeids as a set of values.

    Input: (if any of the parameters are not specified (None), no restrictions
           will be applied for them):
           revision - sourcestamp revision, or list of revisions
           branch_name - branch name
           starttime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
           changeid_all - if True, the query will return 1 row per changeid, 
                thus multiple rows for one build request; 
                if False (the default value), only one row will be returned 
                per build request, with only one of the changeids at random
    Output: dictionary of BuildRequest objects, keyed by (br.brid, br.bid)
    """
    q = BuildRequestsQuery(revision=revision, branch_name=branch_name, 
            starttime=starttime, endtime=endtime, changeid_all=changeid_all)
    q_results = q.execute()

    build_requests = {}
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        brid, bid = params['brid'], params['bid']

        if (brid, bid) not in build_requests:
            build_requests[(brid, bid)] = BuildRequest(**params)
        else:
            build_requests[(brid, bid)].add_changeid(params['changeid'])
            build_requests[(brid, bid)].add_author(params['author'])

    return build_requests

class BuildRequest(object):

    def __init__(self, author=None, bid=None, branch=None, brid=None,
        buildername=None, buildsetid=None, category=None, changeid=None,
        changes_revision=None, claimed_at=None, claimed_by_name=None,
        comments=None, complete=0, complete_at=None, finish_time=None,
        number=None, project=None, revlink=None, revision=None, reason=None, 
        repository=None, results=None, submitted_at=None, ssid=None, 
        start_time=None, when_timestamp=None):
        self.number = number
        self.brid = brid
        self.bid = bid      # build id
        self.branch = branch
        self.branch_name = get_branch_name(branch)
        self.buildername = buildername
        self.ssid = ssid
        self.revision = get_revision(revision) # get at most the first 12 chars
        self.changes_revision = get_revision(changes_revision)

        self.changeid = set([changeid])
        self.when_timestamp = when_timestamp
        self.submitted_at = submitted_at
        self.claimed_at = claimed_at
        self.start_time = start_time
        self.complete_at = complete_at
        self.finish_time = finish_time

        self.claimed_by_name = claimed_by_name
        self.complete = complete
        self.reason = reason
        self.results = results if results != None else NO_RESULT

        self.authors = set([author])
        self.comments = comments
        self.revlink = revlink
        self.category = category
        self.repository = repository 
        self.project = project
        self.buildsetid = buildsetid

        self.status = self._compute_status()

        self.platform = get_platform(buildername)
        self.build_type = get_build_type(buildername) # opt / debug
        self.job_type = get_job_type(buildername)    # build / unittest / talos

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
            # build interrupted (eg slave disconnected) and buildbot 
            # retriggered the build
            return INTERRUPTED

        return MISC                       # what's going on?

    def get_duration(self):
        change_time = self.when_timestamp or self.submitted_at
        return self.complete_at - change_time \
            if self.complete_at and change_time else 0

    def get_wait_time(self):
        change_time = self.when_timestamp or self.submitted_at
        return self.start_time - change_time \
            if self.start_time and change_time else 0

    def get_run_time(self):
        return self.get_duration() - self.get_wait_time()

    def add_changeid(self, changeid):
        self.changeid.add(changeid)

    def add_author(self, author):
        self.authors.add(author)

    def to_dict(self, summary=False):
        json_obj = {
            'number': self.number,
            'brid': self.brid,
            'bid': self.bid,
            'changeid': list(self.changeid),
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
            'authors': [auth for auth in self.authors if auth],
            'comments': self.comments,
            'revlink': self.revlink,
            'category': self.category,
            'repository': self.repository,
            'project': self.project,
            'buildsetid': self.buildsetid,
        }
        return json_obj
