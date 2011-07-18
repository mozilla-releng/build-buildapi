import time

from sqlalchemy import *
import buildapi.model.meta as meta
from buildapi.lib import json

import logging
log = logging.getLogger(__name__)

def requestFromRow(row):
    request = {
        'request_id': row.request_id,
        'buildername': row.buildername,
        'branch': row.branch,
        'revision': row.revision,
        'submittime': row.submitted_at,
        'complete': row.complete,
        'complete_at': row.complete_at,
        'priority': row.priority,
        'claimed_at': row.claimed_at,
        'reason': row.reason,
        }
    return request

def buildFromRow(row, requestProps=False):
    request = requestFromRow(row)
    if requestProps:
        request['properties'] = getRequestProperties(request['request_id'])

    build = {
        'build_id': row.build_id,
        'requests': [request],
        'buildnumber': row.number,
        'buildername': row.buildername,
        'branch': row.branch,
        'revision': row.revision,
        'starttime': row.start_time,
        'endtime': row.finish_time,
        'status': row.results,
        'claimed_by_name': row.claimed_by_name,
        }
    return build

def getRequestProperties(request_id):
    # Get the properties for this request
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    bsp = meta.scheduler_db_meta.tables['buildset_properties']

    props = bsp.select(and_(
        bsp.c.buildsetid == bs.c.id,
        bs.c.id == br.c.buildsetid,
        br.c.id == request_id,
        )).execute().fetchall()
    return dict( (p.property_name, json.loads(p.property_value)[0]) for p in props)

def getRequest(branch, request_id):
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    b = meta.scheduler_db_meta.tables['builds']

    q = select([
        bs.c.id.label('buildset_id'),
        br.c.id.label('request_id'),
        br.c.buildername,
        bs.c.reason,
        ss.c.branch,
        ss.c.revision,
        br.c.results,
        br.c.submitted_at,
        br.c.claimed_at,
        br.c.claimed_by_name,
        br.c.claimed_by_incarnation,
        br.c.priority,
        br.c.complete,
        br.c.complete_at,
        ])
    q = q.where(and_(br.c.buildsetid == bs.c.id, bs.c.sourcestampid==ss.c.id))
    q = q.where(or_(
            ss.c.branch.startswith(branch),
            ss.c.branch.endswith(branch),
    ))
    q = q.where(br.c.id == request_id)
    q = q.limit(1)
    req = q.execute().fetchone()
    if not req:
        return None
    retval = requestFromRow(req)

    # Get the properties for this request
    retval['properties'] = getRequestProperties(request_id)

    # Find build ids for this request
    q = select([b], and_(b.c.brid == req.request_id))
    retval['build_ids'] = [b.id for b in q.execute()]
    return retval

def getBuild(branch, build_id):
    b  = meta.scheduler_db_meta.tables['builds']
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    ss = meta.scheduler_db_meta.tables['sourcestamps']

    q = select([
        b.c.id.label('build_id'),
        br.c.id.label('request_id'),
        b.c.number,
        br.c.buildername,
        ss.c.branch,
        ss.c.revision,
        bs.c.reason,
        b.c.start_time,
        b.c.finish_time,
        br.c.results,
        br.c.submitted_at,
        br.c.claimed_at,
        br.c.claimed_by_name,
        br.c.claimed_by_incarnation,
        br.c.priority,
        br.c.complete,
        br.c.complete_at,
        ])
    q = q.where(and_(br.c.id == b.c.brid, br.c.buildsetid == bs.c.id, bs.c.sourcestampid==ss.c.id))
    q = q.where(or_(
            ss.c.branch.startswith(branch),
            ss.c.branch.endswith(branch),
    ))
    q = q.where(b.c.id == build_id)
    q = q.limit(1)
    build = q.execute().fetchone()
    if not build:
        return None
    return buildFromRow(build, requestProps=True)

def getBuildsQuery(branch, starttime=None, endtime=None, limit=None):
    b  = meta.scheduler_db_meta.tables['builds']
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    ss = meta.scheduler_db_meta.tables['sourcestamps']

    # Find running / complete builds
    q = select([
        b.c.id.label('build_id'),
        br.c.id.label('request_id'),
        b.c.number,
        br.c.buildername,
        bs.c.id,
        bs.c.reason,
        ss.c.branch,
        ss.c.revision,
        b.c.start_time,
        b.c.finish_time,
        br.c.results,
        br.c.submitted_at,
        br.c.claimed_at,
        br.c.claimed_by_name,
        br.c.claimed_by_incarnation,
        br.c.priority,
        br.c.complete,
        br.c.complete_at,
        ])
    q = q.where(and_(
        b.c.brid == br.c.id,
        bs.c.id == br.c.buildsetid,
        ss.c.id == bs.c.sourcestampid,
        ))
    q = q.where(or_(
            ss.c.branch.startswith(branch),
            ss.c.branch.endswith(branch),
    ))
    if starttime:
        q = q.where(b.c.start_time >= starttime)
    if endtime:
        q = q.where(b.c.start_time < endtime)
    q = q.order_by(
        b.c.id.desc(),
        )

    if limit:
        q = q.limit(limit)

    return q

def getPendingQuery(branch, starttime=None, endtime=None, limit=None):
    br = meta.scheduler_db_meta.tables['buildrequests']
    bs = meta.scheduler_db_meta.tables['buildsets']
    ss = meta.scheduler_db_meta.tables['sourcestamps']

    # Find pending builds
    q = select([
        br.c.id.label('request_id'),
        br.c.buildername,
        ss.c.branch,
        ss.c.revision,
        bs.c.reason,
        br.c.submitted_at,
        br.c.claimed_at,
        #br.c.claimed_by_name,
        #br.c.claimed_by_incarnation,
        br.c.priority,
        br.c.complete,
        br.c.complete_at,
        ])
    q = q.where(and_(br.c.buildsetid == bs.c.id, bs.c.sourcestampid==ss.c.id))
    q = q.where(br.c.claimed_at == 0)
    q = q.where(br.c.complete == 0)
    q = q.where(or_(
            ss.c.branch.startswith(branch),
            ss.c.branch.endswith(branch),
    ))
    if starttime:
        q = q.where(br.c.submitted_at >= starttime)
    if endtime:
        q = q.where(br.c.submitted_at < endtime)
    if limit:
        q = q.limit(limit)
    q = q.order_by(
        br.c.submitted_at.desc(),
        )
    return q

def getBuilds(branch, starttime=None, endtime=None, limit=None):
    br = meta.scheduler_db_meta.tables['buildrequests']
    retval = {'builds': [], 'running':[], 'pending': []}

    build_q = getBuildsQuery(branch, starttime, endtime, limit)
    running_builds = build_q.where(br.c.complete == 0)
    old_builds = build_q.where(br.c.complete != 0)

    # Elements with the same claimed_by_name, claimed_by_incarnation,
    # claimed_at, buildername, and number are actually the same build and
    # should only be represented once
    builds = {}
    for btype, q in ( ('running', running_builds), ('builds', old_builds) ):
        for build in q.execute():
            key = (build.claimed_by_name, build.claimed_by_incarnation, build.claimed_at, build.buildername, build.number)
            if key in builds:
                request = requestFromRow(build)
                builds[key]['requests'].append(request)
            else:
                builds[key] = buildFromRow(build)
                retval[btype].append(builds[key])

    q = getPendingQuery(branch, starttime, endtime, limit)
    for req in q.execute():
        retval['pending'].append(requestFromRow(req))

    return retval

def getRevision(branch, revision, starttime=None, endtime=None, limit=None):
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    br = meta.scheduler_db_meta.tables['buildrequests']

    retval = []

    revision = revision[:12]

    # TODO: Look at changes table too to find unscheduled or merged changes.
    build_q = getBuildsQuery(branch, starttime, endtime, limit)
    build_q = build_q.where(ss.c.revision.startswith(revision))

    # Elements with the same claimed_by_name, claimed_by_incarnation,
    # claimed_at, buildername, and number are actually the same build and
    # should only be represented once
    builds = {}
    for build in build_q.execute():
        key = (build.claimed_by_name, build.claimed_by_incarnation, build.claimed_at, build.buildername, build.number)
        if key in builds:
            request = requestFromRow(build)
            builds[key]['requests'].append(request)
        else:
            builds[key] = buildFromRow(build)
            retval.append(builds[key])

    q = getPendingQuery(branch, starttime, endtime, limit)
    q = q.where(ss.c.revision.contains(revision))
    for req in q.execute():
        retval.append(requestFromRow(req))

    return retval

def getBuilders(branch, starttime=None, endtime=None):
    """Returns a lits of builders available on branch between starttime and endtime.

    If starttime and enddtime are None, default to two months ago to now"""
    br = meta.scheduler_db_meta.tables['buildrequests']

    if starttime is None and endtime is None:
        starttime = time.time() - 60*24*3600
        endtime = time.time()

    q = select([br.c.buildername], and_(
        br.c.buildername.contains(branch),
        br.c.submitted_at >= starttime,
        br.c.submitted_at <= endtime,
        )).distinct()

    return [row[0] for row in q.execute()]

def getBuildsForUser(branch, user, starttime=None, endtime=None, limit=None):
    br = meta.scheduler_db_meta.tables['buildrequests']
    ss = meta.scheduler_db_meta.tables['sourcestamps']
    sc = meta.scheduler_db_meta.tables['sourcestamp_changes']
    c = meta.scheduler_db_meta.tables['changes']
    retval = {'builds': [], 'running':[], 'pending': []}

    build_q = getBuildsQuery(branch, starttime, endtime, limit)
    build_q = build_q.where(and_(
        ss.c.id == sc.c.sourcestampid,
        sc.c.changeid == c.c.changeid,
        c.c.author == user,
        ))
    running_builds = build_q.where(br.c.complete == 0)
    old_builds = build_q.where(br.c.complete != 0)

    # Elements with the same claimed_by_name, claimed_by_incarnation,
    # claimed_at, buildername, and number are actually the same build and
    # should only be represented once
    builds = {}
    for btype, q in ( ('running', running_builds), ('builds', old_builds) ):
        for build in q.execute():
            key = (build.claimed_by_name, build.claimed_by_incarnation, build.claimed_at, build.buildername, build.number)
            if key in builds:
                request = requestFromRow(build)
                builds[key]['requests'].append(request)
            else:
                builds[key] = buildFromRow(build)
                retval[btype].append(builds[key])

    q = getPendingQuery(branch, starttime, endtime, limit)
    q = q.where(and_(
        ss.c.id == sc.c.sourcestampid,
        sc.c.changeid == c.c.changeid,
        c.c.author == user,
        ))
    for req in q.execute():
        retval['pending'].append(requestFromRow(req))

    return retval
