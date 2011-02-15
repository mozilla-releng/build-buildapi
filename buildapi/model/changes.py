from sqlalchemy import or_, select, not_

import buildapi.model.meta as meta
from buildapi.model.util import get_revision

c = meta.scheduler_db_meta.tables['changes']

def ChangesQuery(revision=None, branch_name=None, starttime=None, endtime=None):
    """Constructs the sqlalchemy query for fetching changes.

    Input: (if any of the parameters are not specified (None), no restrictions
           will be applied for them):
           revision - sourcestamp revision, or list of revisions
           branch_name - branch name
           starttime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
    Output: query
    """
    q = select([c.c.changeid, c.c.revision, c.c.branch, c.c.when_timestamp])

    if revision:
        if not isinstance(revision, list):
            revision = [revision]
        revmatcher = [c.c.revision.like(rev + '%') for rev in revision if rev]
        if revmatcher:
            q = q.where(or_(*revmatcher))
    if branch_name:
        q = q.where(c.c.branch.like(branch_name + '%'))
    if starttime:
        q = q.where(c.c.when_timestamp >= starttime)
    if endtime:
        q = q.where(c.c.when_timestamp < endtime)

    return q

def PendingChangesQuery(revision=None, branch_name=None, starttime=None, 
    endtime=None):
    """Constructs the sqlalchemy query for fetching pending changes (changes 
    with no build requests yet).

    Input: (if any of the parameters are not specified (None), no restrictions
           will be applied for them):
           revision - sourcestamp revision, or list of revisions
           branch_name - branch name
           starttime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
    Output: query
    """
    c = meta.scheduler_db_meta.tables['changes']
    sch = meta.scheduler_db_meta.tables['sourcestamp_changes']

    return ChangesQuery(revision=revision, branch_name=branch_name, 
            starttime=starttime, endtime=endtime).where(
            not_(c.c.changeid.in_(select([sch.c.changeid]))))

def GetChanges(revision=None, branch_name=None, starttime=None, endtime=None,
    pending_only=False):
    """Fetches all changes matching the parameters, and returns them as 
    a dictionary of changes tuples, keyed by the changeid. 

    Input: (if any of the parameters are not specified (None), no restrictions
           will be applied for them):
           revision - sourcestamp revision, or list of revisions
           branch_name - branch name
           starttime - start time (UNIX timestamp in seconds)
           endtime - end time (UNIX timestamp in seconds)
    Output: dictionary of Change objects keyed by changeid
    """
    if not pending_only:
        q = ChangesQuery(starttime=starttime, endtime=endtime, 
            branch_name=branch_name, revision=revision)
    else:
        q = PendingChangesQuery(starttime=starttime, endtime=endtime, 
            branch_name=branch_name, revision=revision)
    q_results = q.execute()

    changes = {}
    for r in q_results:
        params = dict((str(k), v) for (k, v) in dict(r).items())
        changes[params['changeid']] = Change(**params)

    return changes

class Change(object):

    def __init__(self, changeid=None, revision=None, branch=None,
        when_timestamp=None, ss_revision=None):
        self.changeid = changeid
        self.revision = get_revision(revision)
        self.branch = branch
        self.when_timestamp = when_timestamp
        self.ss_revision = ss_revision  # sourcestamp revision, tentative

    def __repr__(self):
        return '%s(%s,%s)' % (self.changeid, self.branch, self.revision)

    def __str__(self):
        return self.__repr__()
