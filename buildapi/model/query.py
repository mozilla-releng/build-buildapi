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
                    b.c.number,
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

def GetHistoricBuilds(slave, count=20):
    b  = meta.status_db_meta.tables['builds']
    bs = meta.status_db_meta.tables['builders']
    s  = meta.status_db_meta.tables['slaves']
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    q = select([b.c.id,
                bs.c.name.label('buildname'),
                b.c.buildnumber,
                b.c.starttime,
                b.c.endtime,
                b.c.result,
                s.c.name.label('slavename'),
            ])
    q = q.where(and_(b.c.slave_id==s.c.id, b.c.builder_id==bs.c.id))
    q = q.where(b.c.result != None)
    if slave is not None:
      q = q.where(s.c.name==slave)
    # should order b.c.starttime but that's much slower than id
    q = q.order_by(b.c.id.desc()).limit(count)

    query_results = q.execute()

    builds = []
    for r in query_results:
        this_result = {}
        for key,value in r.items():
            this_result[str(key)] = value
        builds.append(this_result)
        print this_result['starttime'].tzinfo

    return builds
