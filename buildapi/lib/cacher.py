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

        try:
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

            try:
                retval = func(*args, **kwargs)
                self._put(key, retval, expire)
                return retval
            finally:
                self._releaselock(readlock)
                self._releaselock(writelock)
        except:
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

        def _getlock(self, key, expire):
            if not hasattr(self.local, 'locks'):
                self.local.locks = {}
            assert key not in self.local.locks
            l = redis.client.Lock(self.r, key, timeout=int(expire-time.time()))
            l.acquire()
            self.local.locks[key] = l

        def _releaselock(self, key):
            self.local.locks[key].release()
            del self.local.locks[key]

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

        def _getlock(self, key, expire):
            # try repeatedly to add the key, which will fail if the key
            # already exists, until we are the one to add it
            delay = 0.001
            while not self.m.add(key, '', expire):
                time.sleep(delay)
                delay = min(delay * 1.1, 1)

        def _releaselock(self, key):
            self.m.delete(key)

except ImportError:
    pass
