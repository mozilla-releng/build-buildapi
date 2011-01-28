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
        readlock = "readlocks:%s" % key
        log.debug("Getting read lock %s", readlock)
        self._getlock(readlock, expire=time.time()+lock_time)
        log.debug("Got read lock %s", readlock)

        try:
            retval = self._get(key)
            self._releaselock(readlock)
            return retval
        except KeyError:
            pass
        except:
            self._releaselock(readlock)
            raise

        writelock = "writelocks:%s" % key
        log.debug("Getting write lock %s", writelock)
        self._getlock(writelock, expire=time.time()+lock_time)
        log.debug("Got write lock %s", writelock)

        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        try:
            retval = func(*args, **kwargs)
            self._put(key, retval, expire)
            return retval
        finally:
            self._releaselock(readlock)
            self._releaselock(writelock)

    def put(self, key, val, expire=0):
        return self._put(key, val, expire)

try:
    import memcache
    class MemcacheLock(object):
        def __init__(self, cache, key):
            self.cache = cache
            self.key = str(key)

        def acquire(self):
            while True:
                now = time.time()
                t = self.cache.add(self.key, now)
                if t:
                    break
                if now - int(self.cache.get(self.key)) > 60:
                    self.cache.delete(self.key)
                time.sleep(1)
            return

        def release(self):
            self.cache.delete(self.key)

    class MemcacheCache(BaseCache):
        def __init__(self, servers=None):
            if servers is None:
                servers = ['localhost:11211']
            self.m = memcache.Client(servers, debug=1)
            self.locks = {}

        def _get(self, key):
            key = str(key)
            retval = self.m.get(key)
            if retval is None:
                raise KeyError
            return json.loads(retval.decode('zlib'))

        def _put(self, key, val, expire=0):
            self.m.set(str(key), json.dumps(val).encode('zlib'), time=expire)

        def has_key(self, key):
            return self.m.get(str(key)) is not None

        def _getlock(self, key, expire):
            l = MemcacheLock(self.m, key)
            l.acquire()
            self.locks[key] = l

        def _releaselock(self, key):
            self.locks[key].release()
            del self.locks[key]

except ImportError:
    pass

try:
    import redis.client
    class RedisCache(BaseCache):
        def __init__(self, host='localhost', port=6379):
            self.r = redis.client.Redis(host, port)
            self.locks = {}

        def _get(self, key):
            if not self.has_key(key):
                raise KeyError

            t = self.r.type(key)
            if t == 'list':
                return [json.loads(x) for x in self.r.lrange(key, 0, -1)]
            else:
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

        #def push(self, key, value):
            #return self.r.rpush(key, json.dumps(value))

        def _getlock(self, key, expire):
            l = redis.client.Lock(self.r, key, timeout=int(expire-time.time()))
            l.acquire()
            self.locks[key] = l

        def _releaselock(self, key):
            self.locks[key].release()
            del self.locks[key]

except ImportError:
    pass
