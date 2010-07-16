from sqlalchemy import *
import buildapi.model.meta as meta
from pylons.decorators.cache import beaker_cache
import math
import time
import re

PLATFORMS_BUILDERNAME = {
    'linux': [re.compile('^Linux (?!x86-64).+')],
    'linux64': [re.compile('^Linux x86-64 .+')],
    'leopard': [re.compile('^OS X 10.5.2 .+')],
    'snowleopard': [re.compile('^OS X 10.6.2 .+')],
    'win2k3': [re.compile('^WINNT 5.2 .+')],
    'maemo4': [re.compile('^Maemo 4 .+')],
    'maemo5qt': [re.compile('^Maemo 5 QT .+')],
    'maemo5gtk': [re.compile('^Maemo 5 GTK .+')],
    'androidr7': [re.compile('^Android R7 .+')],
}

PLATFORMS_BUILDERNAME_EXCLUDE = [
    re.compile('.+ l10n .+'),
]

BUILDSET_REASON_SQL_EXCLUDE = [
    "The web-page 'force build' button was pressed by %",
    "The web-page 'rebuild' button was pressed by %",
]

BUILDPOOL_MASTERS = {
    'buildpool': ['production-master01.build.mozilla.org', 'production-master03.build.mozilla.org'],
    'trybuildpool': ['production-master02.build.mozilla.org'],
}

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

def GetBuilds(branch=None, type='pending'):
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

def GetWaitTimes(pool, minutes_per_block=15, starttime=None, endtime=None):
    starttime, endtime = get_time_interval(starttime, endtime)

    b  = meta.scheduler_db_meta.tables['builds']
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    s = meta.scheduler_db_meta.tables['sourcestamps']
    sch = meta.scheduler_db_meta.tables['sourcestamp_changes']
    c = meta.scheduler_db_meta.tables['changes']
    
    q = join(b, br, b.c.brid==br.c.id) \
               .join(bs, bs.c.id==br.c.buildsetid) \
               .join(s, s.c.id==bs.c.sourcestampid) \
               .outerjoin(sch, sch.c.sourcestampid==s.c.id) \
               .outerjoin(c, c.c.changeid==sch.c.changeid) \
           .select(br.c.complete==1) \
           .with_only_columns([br.c.buildername, b.c.start_time, br.c.submitted_at, c.c.when_timestamp])

    q = q.where(or_(c.c.when_timestamp>=starttime, br.c.submitted_at>=starttime))
    q = q.where(b.c.start_time<=endtime)
        
    # fetch builds only for masters in pool
    masters = BUILDPOOL_MASTERS[pool]
    mnames_matcher = [br.c.claimed_by_name.startswith(master) for master in masters]
    if len(mnames_matcher) > 0:
        q = q.where(or_(*mnames_matcher))
    
    # exclude all rebuilds and forced builds
    rmatcher = [not_(bs.c.reason.like(rpat)) for rpat in BUILDSET_REASON_SQL_EXCLUDE]
    if len(rmatcher) > 0:
	    q = q.where(and_(*rmatcher))

    query_results = q.execute()

    wt = dict(pool=pool, masters=masters, total=0, wt={0:0}, starttime=starttime, endtime=endtime, 
        minutes_per_block=minutes_per_block, platforms={}, otherplatforms=set(), unknownbuilders=set(),
        no_changes=0)
    for r in query_results:
        # start time is changes.when_timestamp, or buildrequests.submitted_at if build has no changes
        stime = r['when_timestamp']
        if not stime:
            stime = r['submitted_at']
            wt['no_changes']+=1
        # end time is builds.start_time
        etime = r['start_time']
        buildername = r['buildername']
        platform = get_platform(buildername)
     
        if not platform:			# excluded
            wt['unknownbuilders'].add(buildername)
            continue

        if platform == 'other':		# other platforms (NOT excluded)
            wt['otherplatforms'].add(buildername)
     
        duration_min = (etime - stime)/60.0
        block_no = int(math.floor(duration_min/minutes_per_block))*minutes_per_block
     
        update_wait_time(wt, platform, block_no)
     	
    wt['otherplatforms'] = list(wt['otherplatforms'])		# sets are not JSON serializable 
    wt['unknownbuilders'] = list(wt['unknownbuilders'])	# make lists

    return wt

def update_wait_time(wt, p, block_no):
	# update overall wait times
    wt['wt'][block_no] = wt['wt'].get(block_no, 0) + 1
    wt['total'] += 1

    # update platform specific wait times
    if p not in wt['platforms']:
        wt['platforms'][p] = dict(total=0, wt={0:0})
    wt['platforms'][p]['wt'][block_no] = wt['platforms'][p]['wt'].get(block_no, 0) + 1
    wt['platforms'][p]['total'] += 1

def get_platform(buildername):
    bname = buildername.lower()
    
    if any(filter(lambda p: p.match(buildername), PLATFORMS_BUILDERNAME_EXCLUDE)):
        return None

    for platform in PLATFORMS_BUILDERNAME:
        for pat in PLATFORMS_BUILDERNAME[platform]:
            if pat.match(buildername):
                return platform

    return 'other'

def get_time_interval(starttime, endtime):
    if not endtime:
        endtime = min(starttime+24*3600 if starttime else time.time(), time.time())
    if not starttime:
        starttime = endtime-24*3600

    return starttime, endtime
