import threading
import time
import mock
from buildapi.lib import cacher
from unittest import TestCase

class Cases(object):

    def test_get(self):
        m = mock.Mock()
        m.return_value = 7
        self.assertEqual(self.c.get('not-there', m,
                args=(1, 2), kwargs=dict(a='a', b='b')),
            7)
        m.assert_called_with(1, 2, a='a', b='b')
        m.clear()

        # and the second time, it's in the cache
        self.assertEqual(self.c.get('not-there', m), 7)
        m.assert_not_called()

    def test_put(self):
        m = mock.Mock()
        self.c.put('not-there', 7)
        self.assertEqual(self.c.get('not-there', m), 7)
        m.assert_not_called()
        self.c.put('not-there', 8)
        self.assertEqual(self.c.get('not-there', m), 8)
        m.assert_not_called()

    def test_has_key(self):
        self.c.put('there', 'there')
        self.assertFalse(self.c.has_key('not-there'))
        self.assertTrue(self.c.has_key('there'))

    def test_race(self):
        # this is to test a thundering-herd problem when a key is missing and
        # multiple gets occur at the same time.  It uses a "slow" function to
        # generate the result, and then just throws a lot of threads at it.
        # This will either fail "sometimes" or not at all, unfortunately.
        # Testing for race conditions is hard, since they are inherently
        # sometimes harmless.
        calls = []
        def generate(thd):
            calls.append(thd)
            time.sleep(0.1)
        def get(thd):
            c = self.newCache() if thd else self.c
            c.get('not-there', generate, args=(thd,), lock_time=2)
        thds = [ threading.Thread(target=get, args=(i,))
                 for i in range(10) ]
        for thd in thds:
            thd.start()
        for thd in thds:
            thd.join()
        self.assertEqual(len(calls), 1, calls)

    # TODO: lists?

class TestRedisCacher(TestCase, Cases):

    def newCache(self):
        return cacher.RedisCache()

    def setUp(self):
        self.c = self.newCache()
        self.c.r.delete('not-there')

    def tearDown(self):
        self.c.r.delete('there')
        self.c.r.delete('not-there')


class TestMemcacheCacher(TestCase, Cases):

    def newCache(self):
        return cacher.MemcacheCache()

    def setUp(self):
        self.c = self.newCache()
        self.c.m.delete('not-there')

    def tearDown(self):
        self.c.m.delete('there')
        self.c.m.delete('not-there')

