#!/usr/bin/python

import sys, os
from optparse import OptionParser
from ConfigParser import SafeConfigParser
import json

import sqlalchemy as sa
from datetime import datetime, timedelta

import calendar
import time

import buildapi.model.statusdb_orm as model


def encode_dates(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt2epoch(dt)
    else:
        return dt


def td2secs(td):
    """Return the number of seconds in the given timedelta object"""
    return td.seconds + td.days*3600*24


def dt2epoch(dt):
    t = dt.utctimetuple()
    return calendar.timegm(t)


def avg(l):
    if len(l) == 0:
        return 0
    return sum(l) / len(l)


def req2json(r):
    changes = []
    if r.source.changes:
        for change in r.source.changes:
            change = change.change
            files = [f.path for f in change.files]
            changes.append({
                'who': change.who,
                'revision': change.revision,
                'comments': change.comments,
                'when': change.when,
                'files': files,
                })

    return {'changes': changes,
            'revision': r.source.revision,
            'branch': r.source.branch,
            'when': r.submittime,
           }


def get_request_info(scheduler_db, build, props):
    if 'buildername' not in props:
        return ([], None)

    # Look for request_ids / request_times props
    if 'request_ids' in props and 'request_times' in props:
        return (props['request_ids'], min(props['request_times'].values()))

    q = scheduler_db.execute(sa.text("""\
            select buildrequests.id, submitted_at from buildrequests, builds where
                buildrequests.id = builds.brid and
                buildrequests.buildername = :buildername and
                builds.number = :buildnumber and
                abs(builds.start_time - :start_time) < 2"""),
            buildername=props['buildername'],
            buildnumber=build.buildnumber,
            start_time=dt2epoch(build.starttime),
            )

    first_request_time = None
    request_ids = []
    for request_id, request_time in q:
        request_ids.append(request_id)
        if first_request_time is None:
            first_request_time = request_time
        else:
            first_request_time = min(first_request_time, request_time)

    return (request_ids, first_request_time)


class Cache(object):

    @staticmethod
    def new(config):
        cache_spec = config.get('general', 'cache', None)
        if not cache_spec:
            return Cache()
        if cache_spec.startswith("memcached:"):
            hosts = cache_spec[10:].split(',')
            return MemcacheCache(hosts)
        raise RuntimeError("invalid cache spec %r" % (cache_spec,))

    def get(self, key):
        return None

    def put(self, key, val, expire=0):
        pass


class MemcacheCache(Cache):

    def __init__(self, hosts):
        import memcache
        self.m = memcache.Client(hosts)

    def _utf8(self, s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    def get(self, key):
        return self.m.get(self._utf8(key))

    def put(self, key, val, expire=0):
        if expire == 0:
            self.m.set(self._utf8(key), val)
        else:
            self.m.set(self._utf8(key), val, expire)


def build_report(cache, session, scheduler_db, starttime, endtime, include_steps=False):
    builds = []
    report = {'builds': builds, 'starttime': starttime, 'endtime': endtime}

    s = time.time()

    q = session.query(model.Build).filter(
            sa.and_(model.Build.endtime >= starttime, model.Build.endtime <= endtime))
    q = q.order_by(model.Build.starttime)
    #q = q.options(sa.orm.eagerload('properties'))

    all_builds = list(q)
    e = time.time()
    print "%.2f get builds" % (e-s)

    s = time.time()

    n = len(all_builds)
    i = 0
    misses = [0]

    times = {'builds': 0}

    for build in all_builds:
        i += 1

        def get_build_dict():
            #print "Getting build info"
            misses[0] += 1
            s0 = time.time()
            props = {}
            try:
                for prop in build.properties:
                    props[prop.name] = prop.value
            except:
                pass # Properties values are unparsable

            # Figure out this build's request ids from the scheduler db
            request_ids, requesttime = get_request_info(scheduler_db, build, props)

            build_dict = {
                'id': build.id,
                'builder_id': build.builder_id,
                'slave_id': build.slave.id,
                'master_id': build.master_id,
                'starttime': dt2epoch(build.starttime),
                'endtime': dt2epoch(build.endtime),
                'result': build.result,
                'reason': build.reason,
                'properties': props,
                'buildnumber': build.buildnumber,
                'request_ids': request_ids,
                'requesttime': requesttime,
                }

            if include_steps:
                steps = []
                for s in build.steps:
                    steps.append({
                        'name': s.name,
                        'starttime': s.starttime,
                        'enddtime': s.endtime,
                        'status': s.status,
                    })
                build_dict['steps'] = steps
            times['builds'] += time.time() - s0
            return build_dict

        build_key = 'builds:%i' % build.id
        build_dict = cache.get(build_key)
        if build_dict is not None:
            try:
                build_dict = json.loads(build_dict.decode("zlib"))
            except:
                cache.put(build_key, build_dict.encode("zlib"), 24*3600)
                build_dict = json.loads(build_dict)
        else:
            build_dict = get_build_dict()
            cache.put(build_key, json.dumps(build_dict).encode("zlib"), 24*3600)
        builds.append(build_dict)

    e = time.time()
    print "%.2f generate report. %i/%i missed" % (e-s, misses[0], n)
    print times

    return report

if __name__ == "__main__":

    def timedelta_option(option, opt, value, parser, units):
        setattr(parser.values, option.dest, timedelta(seconds=value * units))

    def ts_option(option, opt, value, parser):
        setattr(parser.values, option.dest, datetime.utcfromtimestamp(value))

    def date_option(option, opt, value, parser):
        setattr(parser.values, option.dest, datetime.strptime(value, "%Y-%m-%d"))

    parser = OptionParser("%prog [options]")
    parser.set_defaults(
        report_window = timedelta(seconds=3600*24), # 1 day
        start_time = datetime.utcnow() - timedelta(days=1),
        compression = None,
        output = None,
        compact = False,
        report = "build",
        config = "reporter.cfg",
        list_builders = None,
        list_masters = False,
        )

    parser.add_option("", "--days", type="int", dest="report_window",
            action="callback",
            help="How many days to report", callback=timedelta_option,
            callback_kwargs={'units': 3600*24})
    parser.add_option("", "--hours", type="int", dest="report_window",
            action="callback",
            help="How many hours to report", callback=timedelta_option,
            callback_kwargs={'units': 3600})
    parser.add_option("", "--starttime", type="int", dest="start_time",
            action="callback",
            help="What time to use as the beginning of the report, as a unix timestamp",
            callback=ts_option)
    parser.add_option("", "--startdate", type="string", dest="start_time",
            action="callback",
            help="What date to use as the beginning of the report, as YYYY-MM-DD",
            callback=date_option)
    parser.add_option("-z", "--gzip", action="store_const", dest="compression",
            const="gzip", help="Compress output with gzip")
    parser.add_option("-o", "--output", dest="output",
            help="output to specified file (default, or '-', for stdout)")
    parser.add_option("", "--compact", dest="compact", action="store_true",
            help="generate compact json output")
    parser.add_option("-c", "--config", dest="config")
    parser.add_option("", "--dburl", dest="dburl")
    parser.add_option("-l", "--list-builders", dest="list_builders")
    parser.add_option("-m", "--list-masters", dest="list_masters",
            action="store_true")

    options, args = parser.parse_args()

    if not options.output or options.output == "-":
        fp = sys.stdout
    else:
        fp = open(options.output + ".tmp", "w")

    config = SafeConfigParser()
    if options.config:
        config.read(options.config)

    if not options.dburl:
        if not config.has_option('general', 'dburl'):
            parser.error("A DB URL must be specified either on the command line or via the config file")
        options.dburl = config.get('general', 'dburl')

    if not config.has_option('general', 'scheduler_dburl'):
        parser.error("scheduler_dburl must be specified in the config file")

    if options.compression == "gzip":
        import gzip
        fp = gzip.GzipFile(fileobj=fp)

    session_maker = model.connect(options.dburl, pool_recycle=60)
    session = session_maker()

    scheduler_db_engine = sa.create_engine(config.get('general', 'scheduler_dburl'), pool_recycle=60)

    starttime = options.start_time
    endtime = starttime + options.report_window

    start = datetime.now()
    if options.compact:
        encoder = json.JSONEncoder(default=encode_dates, sort_keys=True,
                separators=(',', ':'))
    else:
        encoder = json.JSONEncoder(default=encode_dates, sort_keys=True,
                indent=2)

    pools = {}
    if config.has_section('pools'):
        for pool, builders in config.items('pools'):
            for builder in builders.split(","):
                pools[builder.strip()] = pool

    if options.list_masters:
        for master in session.query(model.Master):
            fp.write("%s %s\n" % (master.id, master.name))
    elif options.list_builders:
        master = session.query(model.Master).get(options.list_builders)
        if not master:
            master = session.query(model.Master).filter_by(name=unicode(options.list_builders)).first()
        if not master:
            parser.error("Couldn't find master %s" % options.list_builders)

        for builder in session.query(model.Builder).filter_by(master=master):
            fp.write("%s %s\n" % (builder.id, builder.name))

    else:
        print time.asctime()
        cache = Cache.new(config)
        report = build_report(cache, session, scheduler_db_engine, starttime, endtime)

        fp.write(encoder.encode(report))

        if fp != sys.stdout:
            fp.close()
            os.rename(options.output + ".tmp", options.output)

        end = datetime.now()

        print "Report generated in", end-start
