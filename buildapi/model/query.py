from sqlalchemy import *
import buildapi.model.meta as meta
from buildapi.model.util import get_time_interval
from pylons.decorators.cache import beaker_cache

import math, re, time

@beaker_cache(expire=600, cache_response=False)
def GetAllBranches():
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    q = select([ss.c.branch]).distinct()
    q = q.where(not_(ss.c.branch.like("%unittest")))
    results = q.execute()

    # exclude defunct branches
    exclusions = ('releases/mozilla-1.9.3',
                 )

    branches = []
    for r in results:
        if r['branch'] not in exclusions:
            # return last part of releases/mozilla-1.9.2, users/bob/foo
            branches.append(r['branch'].split('/')[-1])

    return sorted(branches)

def GetBranchName(longname):
    # nightlies don't have a branch set (bug 570814)
    if not longname:
        return None

    allBranches = GetAllBranches()
    shortname = longname.split('/')[-1]
    for branch in allBranches:
       if shortname.startswith(branch):
           return branch

    return 'Unknown'

def GetBuilds(branch=None, type='pending', rev=None):
    b  = meta.scheduler_db_meta.tables['builds']
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    if type == 'pending':
        q = select([ss.c.branch,
                    ss.c.revision,
                    br.c.buildername,
                    br.c.submitted_at,
            ])
        q = q.where(and_(br.c.buildsetid==bs.c.id, bs.c.sourcestampid==ss.c.id))
        q = q.where(and_(br.c.claimed_at==0, br.c.complete==0))
    elif type == 'running':
        q = select([ss.c.branch,
                    ss.c.revision,
                    br.c.buildername,
                    br.c.submitted_at,
                    br.c.claimed_at.label('last_heartbeat'),
                    br.c.claimed_by_name,
                    b.c.start_time,
                    b.c.number,
            ])
        q = q.where(and_(b.c.brid == br.c.id,
                         br.c.buildsetid==bs.c.id,
                         bs.c.sourcestampid==ss.c.id))
        q = q.where(and_(br.c.claimed_at > 0,br.c.complete == 0))
    # use an outer join to catch pending builds
    # can probably trim the list of columns a bunch
    elif type == 'revision':
        q = join(br, bs, br.c.buildsetid==bs.c.id) \
                .join(ss, bs.c.sourcestampid==ss.c.id) \
                .outerjoin(b, br.c.id == b.c.brid) \
                .select(ss.c.revision.like(rev[0] + '%')) \
                .with_only_columns([
                    br.c.id,
                    br.c.buildsetid,
                    ss.c.branch,
                    ss.c.revision,
                    br.c.buildername,
                    br.c.submitted_at,
                    br.c.claimed_at,
                    br.c.claimed_by_name,
                    b.c.start_time,
                    b.c.finish_time,
                    b.c.number,
                    br.c.results])

    # ignore nightlies, bug 570814
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
            if key not in ('branch','revision'):
                this_result[key] = value
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

def GetPushes(branch, fromtime, totime):
    ch    = meta.scheduler_db_meta.tables['changes']
    ss_ch = meta.scheduler_db_meta.tables['sourcestamp_changes']
    ss    = meta.scheduler_db_meta.tables['sourcestamps']

    # this is a little complicated in order to cope with mobile
    # adding a second sourcestamp for every revision in m-c (etc).
    # get distinct revision/branch pairs from sourcestamps and
    # retrieve author from changes
    q = select([ss.c.revision, ss.c.branch, ch.c.author],
               and_(ss_ch.c.changeid == ch.c.changeid,
                    ss.c.id == ss_ch.c.sourcestampid))
    q = q.distinct()

    q = q.where(not_(ch.c.branch.like('%unittest')))
    if branch is not None:
        q = q.where(ch.c.branch.like('%' + branch + '%'))

    if fromtime is not None:
        q = q.where(ch.c.when_timestamp >= fromtime)
    if totime is not None:
        q = q.where(ch.c.when_timestamp <= totime)

    query_results = q.execute()
    pushes = {'TOTAL': 0}
    for r in query_results:
        a = r['author']
        if a not in pushes:
            pushes[a] = 0
        pushes[a] += 1
        pushes['TOTAL'] += 1

    return pushes
