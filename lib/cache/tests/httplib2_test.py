#!/usr/bin/python2.5

import test_utils
test_utils.init_appengine()
test_utils.init_httplib2()

import unittest
import datastore
import memory
import layered
from google.appengine.api import memcache
import httplib2

class HttpLib2Test(unittest.TestCase):

  def testHttpLib2(self):
    memory_cache = memory.Client()
    datastore_cache = datastore.Client()
    memcache_cache = memcache.Client()
    caches = [memory_cache, memcache_cache, datastore_cache]
    layered_cache = layered.Client(caches)
    layered_cache.flush_all()
    for cache in caches:
      self.assertEquals(0, cache.get_stats()['items'])
      self.assertEquals(0, cache.get_stats()['misses'])
      self.assertEquals(0, cache.get_stats()['hits'])
    http_client = httplib2.Http(layered_cache)
    url = 'http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js'
    # Fetch it once
    response, content = http_client.request(url)
    self.assertEquals(200, response.status)
    self.assertTrue('jQuery' in content)
    for cache in caches:
      self.assertEquals(1, cache.get_stats()['items'])
      self.assertEquals(1, cache.get_stats()['misses'])
      self.assertEquals(0, cache.get_stats()['hits'])
    # Fetch it again
    response, content = http_client.request(url)
    self.assertEquals(200, response.status)
    self.assertTrue('jQuery' in content)
    for cache in caches:
      self.assertEquals(1, cache.get_stats()['items'])
      self.assertEquals(1, cache.get_stats()['misses'])
    self.assertEquals(1, memory_cache.get_stats()['hits'])
    self.assertEquals(0, memcache_cache.get_stats()['hits'])
    self.assertEquals(0, datastore_cache.get_stats()['hits'])
    # Clear the memory cache and try again
    memory_cache.flush_all()
    self.assertEquals(0, memory_cache.get_stats()['items'])
    self.assertEquals(0, memory_cache.get_stats()['hits'])
    self.assertEquals(0, memory_cache.get_stats()['misses'])
    response, content = http_client.request(url)
    self.assertEquals(200, response.status)
    self.assertTrue('jQuery' in content)
    # TODO(dewitt): In theory, memory_cache should be repopulated
    self.assertEquals(0, memory_cache.get_stats()['items'])
    self.assertEquals(1, memcache_cache.get_stats()['items'])
    self.assertEquals(1, datastore_cache.get_stats()['items'])
    self.assertEquals(0, memory_cache.get_stats()['hits'])
    self.assertEquals(1, memcache_cache.get_stats()['hits'])
    self.assertEquals(0, datastore_cache.get_stats()['hits'])
    # Try one more time
    response, content = http_client.request(url)
    self.assertEquals(200, response.status)
    self.assertTrue('jQuery' in content)
    # TODO(dewitt): In theory, memory_cache should be repopulated
    self.assertEquals(0, memory_cache.get_stats()['items'])
    self.assertEquals(1, memcache_cache.get_stats()['items'])
    self.assertEquals(1, datastore_cache.get_stats()['items'])
    self.assertEquals(0, memory_cache.get_stats()['hits'])
    self.assertEquals(2, memory_cache.get_stats()['misses'])
    self.assertEquals(2, memcache_cache.get_stats()['hits'])
    self.assertEquals(1, memcache_cache.get_stats()['misses'])
    self.assertEquals(0, datastore_cache.get_stats()['hits'])

def suite():
  suite = unittest.TestSuite()
  suite.addTests(unittest.makeSuite(HttpLib2Test))
  return suite

if __name__ == '__main__':
  unittest.main()

