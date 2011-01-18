"""The application's Globals object"""

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from buildapi.lib import json

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
