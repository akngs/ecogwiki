#!/usr/bin/python2.5
#
# Test the cache.layered.Client class.
#
# Copyright 2009 DeWitt Clinton
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import test_utils
test_utils.init_appengine()

import cache_test
import layered
import datastore
import memory
import unittest

import google.appengine.api.apiproxy_stub_map as apiproxy_stub_map
import google.appengine.api.memcache as memcache


class _TestLayeredClient(layered.Client):
  """A wrapper around a layered client that automatically configures itself."""
  def __init__(self, *args, **kwargs):
    memory_cache = memory.Client(*args, **kwargs)
    memcache_cache = _TestMemcacheClient(*args, **kwargs)
    datastore_cache = datastore.Client(*args, **kwargs)
    caches = [memory_cache, memcache_cache, datastore_cache]
    super(_TestLayeredClient, self).__init__(caches, *args, **kwargs)


class _TestMemcacheClient(memcache.Client):
  """Wrapper around the memcache client that exposes gettime."""

  def __init__(self, gettime=None, *args, **kwargs):
    super(_TestMemcacheClient, self).__init__(*args, **kwargs)
    memcache_service_stub = apiproxy_stub_map.apiproxy.GetStub('memcache')
    if gettime:
      memcache_service_stub._gettime.update(gettime())
    else:
      memcache_service_stub._gettime.reset()


class ClientTest(cache_test.ClientTest):

  def __init__(self, *args, **kwargs):
    super(ClientTest, self).__init__(_TestLayeredClient, *args, **kwargs)

  def testDefaultExpiresIn(self):
    """Overriden.  Not in the standard memcache library."""
    pass

  def testGetStats(self):
    """Overriden.  Not sure how to report aggregate stats."""
    pass


def suite():
  suite = unittest.TestSuite()
  suite.addTests(unittest.makeSuite(ClientTest))
  return suite


if __name__ == '__main__':
  unittest.main()
