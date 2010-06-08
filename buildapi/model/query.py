from sqlalchemy import *
import buildapi.model.meta as meta

def GetBranchName(longname):
    # nightlies don't have a branch set (FIXME)
    if not longname:
        return None

    branch = longname

    # handle releases/mozilla-1.9.2, projects/foo, users/bob/foopy
    # by taking the part after the last '/'
    branch = branch.split('/')[-1]

    # handle unit 'branches' by trimming off '-platform-buildtype-test'
    # eg mozilla-central-win32-opt-unittest
    #    addonsmgr-linux-debug-unittest
    if branch.endswith('unittest'):
        branch = '-'.join(branch.split('-')[0:-3])

    # trim off any leading 'l10n-' ??

    return branch

def GetBuilds(branch=None, type='pending'):
    b  = meta.scheduler_db_meta.tables['builds']
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    if type == 'pending':
        q = select([br.c.id,
                    br.c.buildsetid,
                    ss.c.branch,
                    ss.c.revision,
                    br.c.buildername,
                    br.c.submitted_at,
            ])
        q = q.where(and_(br.c.buildsetid==bs.c.id, bs.c.sourcestampid==ss.c.id))
        q = q.where(br.c.claimed_at == 0)
    elif type == 'running':
        q = select([br.c.id,
                    br.c.buildsetid,
                    ss.c.branch,
                    ss.c.revision,
                    br.c.buildername,
                    br.c.submitted_at,
                    br.c.claimed_at,
                    br.c.claimed_by_name,
                    b.c.start_time,
            ])
        q = q.where(and_(b.c.brid == br.c.id,
                         br.c.buildsetid==bs.c.id,
                         bs.c.sourcestampid==ss.c.id))
        q = q.where(and_(br.c.claimed_at > 0,br.c.complete == 0))

    # ignore nightlies, FIXME ?
    q = q.where(ss.c.revision != None)
    if branch is not None:
      q = q.where(ss.c.branch.like('%' + branch[0] + '%'))

    query_results = q.execute()

    builds = {}
    for r in query_results:
        real_branch = GetBranchName(r['branch'])
        revision = r['revision'][:12]
        if real_branch not in builds:
            builds[real_branch] = {}
        if revision not in builds[real_branch]:
            builds[real_branch][revision] = []

        this_result = {}
        for key,value in r.items():
            this_result[key] = value
        this_result['branch'] = real_branch
        builds[real_branch][revision].append(this_result)

    return builds
