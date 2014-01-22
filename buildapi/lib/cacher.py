import threading
import time
try:
    import simplejson as json
except ImportError:
    import json

import logging
log = logging.getLogger(__name__)

class BaseCache:
    def has_key(self, key):
        raise NotImplementedError()

    def get(self, key, func, args=None, kwargs=None, expire=0, lock_time=600):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        # note that in a "thundering herd" situation, this may generate the
        # same cached value several times.  That's OK.
        try:
            try:
                return self._get(key)
            except KeyError:
                retval = func(*args, **kwargs)
                self._put(key, retval, expire)
                return retval
        except Exception:
            log.exception("Problem with cache!")
            return func(*args, **kwargs)

    def put(self, key, val, expire=0):
        return self._put(key, val, expire)

try:
    import redis.client
    class RedisCache(BaseCache):
        def __init__(self, host='localhost', port=6379):
            self.r = redis.client.Redis(host, port)
            # use a thread-local object for holding locks, so that different
            # threads can use locks without stepping on feet
            self.local = threading.local()

        def _get(self, key):
            if not self.has_key(key):
                raise KeyError

            retval = self.r.get(key)
            if retval is not None:
                return json.loads(retval)
            return None

        def _put(self, key, val, expire=0):
            val = json.dumps(val)
            if expire == 0:
                self.r.set(key, val)
            else:
                expire = int(expire - time.time())
                self.r.setex(key, val, expire)

        def has_key(self, key):
            return self.r.exists(key)

except ImportError:
    pass

try:
    import memcache
    class MemcacheCache(BaseCache):
        def __init__(self, hosts=['localhost:11211']):
            self.m = memcache.Client(hosts)

        def _get(self, key):
            retval = self.m.get(key)
            if retval is None:
                raise KeyError
            else:
                return json.loads(retval)

        def _put(self, key, val, expire=0):
            val = json.dumps(val)
            if expire == 0:
                self.m.set(key, val)
            else:
                expire = int(expire - time.time())
                self.m.set(key, val, expire)

        def has_key(self, key):
            return self.m.get(key) is not None

except ImportError:
    pass
