#!/usr/bin/python2.5
#
# Test the google.appengine.api.memcache.Client class.
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
import unittest

import google.appengine.api.apiproxy_stub_map as apiproxy_stub_map
import google.appengine.api.memcache as memcache


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
    super(ClientTest, self).__init__(_TestMemcacheClient, *args, **kwargs)

  def testStringIncr(self):
    """Overridden."""
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', '0'))
    # The memcache client (incorrectly?) doesn't cast str here
    self.assertEquals(1, client.incr('a'))
    self.assertEquals('1', client.get('a'))
    # The memcache client (incorrectly?) doesn't cast str here
    self.assertEquals(11, client.incr('a', delta=10))
    self.assertEquals('11', client.get('a'))

  def testStringDecr(self):
    """Overriden."""
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', '11'))
    # The memcache client (incorrectly?) doesn't cast str here
    self.assertEquals(10, client.decr('a'))
    self.assertEquals('10', client.get('a'))
    # The memcache client (incorrectly?) doesn't cast str here
    self.assertEquals(0, client.decr('a', delta=10))
    self.assertEquals('0', client.get('a'))

  def testDefaultExpiresIn(self):
    """Overriden.  Not in the standard memcache library."""
    pass

def suite():
  suite = unittest.TestSuite()
  suite.addTests(unittest.makeSuite(ClientTest))
  return suite


if __name__ == '__main__':
  unittest.main()
