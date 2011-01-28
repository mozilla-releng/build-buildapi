"""The application's Globals object"""

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

import pytz

from buildapi.lib import json
from buildapi.lib import cacher, cache

class Globals(object):
    """Globals acts as a container for objects available throughout the
    life of the application

    """

    def __init__(self, config):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """
        self.cache = CacheManager(**parse_cache_config_options(config))

        self.buildbot_masters = {}

        # TODO: Support loading this from a URL and refreshing on occasion?
        master_file = config['master_list']

        masters = json.load(open(master_file))

        for master in masters:
            self.buildbot_masters[master['db_name']] = master

        cache_spec = config.get('buildapi.cache')
        tz_name = config.get('timezone')
        tz = pytz.timezone(tz_name)
        self.tz = tz

        # TODO: handle other hosts/ports
        if cache_spec.startswith('memcached:'):
            self.buildapi_cache = cache.BuildapiCache(cacher.MemcacheCache(), tz)
        elif cache_spec.startswith('redis:'):
            self.buildapi_cache = cache.BuildapiCache(cacher.RedisCache(), tz)
        else:
            self.buildapi_cache = None
