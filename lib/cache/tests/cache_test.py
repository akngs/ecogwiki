#!/usr/bin/python2.5
#
# Test cache Clients.
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

import unittest
import test_utils
import time


class TestObject(object):
  def __init__(self, value):
    self._value = value

  def __eq__(self, other):
    return self._value == other._value


class ClientTest(unittest.TestCase):

  def __init__(self, client, *args, **kwargs):
    """Tests instances of client."""
    super(ClientTest, self).__init__(*args, **kwargs)
    self._client = client
  
  def testInit(self):
    client = self._client()

  def testSet(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('', ''))
    self.assertTrue(client.set('a', 'a'))
    self.assertTrue(client.set('bool', True))
    self.assertTrue(client.set('list', ['a', 'b', 'c']))
    self.assertTrue(
      client.set('dict', dict([('a', 'a'), ('b', 'b'), ('c', 'c')])))
    self.assertTrue(client.set('object', TestObject('kittens')))

  def testBadSetKey(self):
    client = self._client()
    self.assertRaises(BaseException, client.set, None, None)

  def testSetIgnoresHashForm(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set(('ingored', 'a'), 'a'))
    self.assertEquals('a', client.get('a'))

  def testGet(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('', ''))
    self.assertEquals('', client.get(''))
    self.assertTrue(client.set('a', 'a'))
    self.assertEquals('a', client.get('a'))
    self.assertTrue(client.set('bool', True))
    self.assertEquals(True, client.get('bool'))
    self.assertTrue(client.set('list', ['a', 'b', 'c']))
    self.assertEquals(['a', 'b', 'c'], client.get('list'))
    self.assertTrue(client.set('dict', {'a': 'a', 'b': 'b', 'c': 'c'}))
    self.assertEquals({'a': 'a', 'b': 'b', 'c': 'c'}, client.get('dict'))
    obj = TestObject('kittens')
    self.assertTrue(client.set('object', obj))
    self.assertEquals(obj, client.get('object'))

  def testBadGetKey(self):
    client = self._client()
    self.assertRaises(BaseException, client.get, None, None)

  def testNamespaces(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    client.set('a', 'a-default')
    self.assertEquals('a-default', client.get('a'))
    client.set('a', 'a-1', namespace='1')
    self.assertEquals('a-1', client.get('a', namespace='1'))
    client.set('a', 'a-2', namespace='2')
    self.assertEquals('a-2', client.get('a', namespace='2'))
    self.assertEquals('a-1', client.get('a', namespace='1'))
    self.assertEquals('a-default', client.get('a'))

  def testClassData(self):
    client_one = self._client()
    client_one.flush_all()
    client_one.set('a', 'a')
    client_two = self._client()
    self.assertEquals('a', client_two.get('a'))

  def testNoExpire(self):
    client_one = self._client()
    client_one.flush_all()
    client_one.set('a', 'a')
    self.assertEquals('a', client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(20))
    self.assertEquals('a', client_two.get('a'))
    self.assertEquals('a', client_one.get('a'))

  def testExpiresIn(self):
    client_one = self._client()
    self.assertTrue(client_one.flush_all())
    self.assertTrue(client_one.set('a', 'a', time=10))
    self.assertEquals('a', client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(20))
    self.assertEquals(None, client_two.get('a'))
    self.assertEquals(None, client_one.get('a'))

  def testExpiresAt(self):
    client_one = self._client()
    self.assertTrue(client_one.flush_all())
    self.assertTrue(client_one.set('a', 'a', time=10))
    self.assertTrue(client_one.set('b', 'b', time=time.time() + 10))
    self.assertEquals('a', client_one.get('a'))
    self.assertEquals('b', client_one.get('b'))
    client_two = self._client(gettime=test_utils.Time(20))
    self.assertEquals(None, client_two.get('a'))
    self.assertEquals(None, client_two.get('b'))

  def testSetMulti(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertEquals([], client.set_multi({'a': 'a', 'b': 'b'}))
    self.assertEquals('a', client.get('a'))
    self.assertEquals('b', client.get('b'))

  def testGetMulti(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertTrue(client.set('b', 'b'))
    values = client.get_multi(['a', 'b'])
    self.assertEquals('a', values['a'])
    self.assertEquals('b', values['b'])

  def testSetMultiWithPrefix(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertEquals([], client.set_multi({'a': 'a', 'b': 'b'}, key_prefix='1-'))
    self.assertEquals('a', client.get('1-a'))
    self.assertEquals('b', client.get('1-b'))

  def testGetMultiWithPrefix(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('1-a', 'a'))
    self.assertTrue(client.set('1-b', 'b'))
    values = client.get_multi(['a', 'b'], key_prefix='1-')
    self.assertEquals('a', values['a'])
    self.assertEquals('b', values['b'])

  def testDelete(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertTrue(client.set('a', 'a', namespace='1'))
    self.assertEquals('a', client.get('a'))
    self.assertEquals('a', client.get('a', namespace='1'))
    self.assertTrue(client.delete('a'))
    self.assertEquals(None, client.get('a'))
    self.assertEquals('a', client.get('a', namespace='1'))
    self.assertTrue(client.delete('a', namespace='1'))
    self.assertEquals(None, client.get('a', namespace='1'))

  def testDeleteWithAddLock(self):
    client_one = self._client()
    self.assertTrue(client_one.flush_all())
    self.assertTrue(client_one.set('a', 'a'))
    self.assertEquals('a', client_one.get('a'))
    self.assertTrue(client_one.delete('a', seconds=10))
    self.assertEquals(None, client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(5))
    self.assertEquals(None, client_two.get('a'))
    self.assertFalse(client_two.add('a', 'a'))
    self.assertEquals(None, client_two.get('a'))
    client_three = self._client(gettime=test_utils.Time(15))
    self.assertEquals(None, client_three.get('a'))
    self.assertTrue(client_three.add('a', 'a'))
    self.assertEquals('a', client_three.get('a'))

  def testDeleteMulti(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertTrue(client.set('b', 'b'))
    self.assertEquals('a', client.get('a'))
    self.assertEquals('b', client.get('b'))
    self.assertTrue(client.delete_multi(['a', 'b']))
    self.assertEquals(None, client.get('a'))
    self.assertEquals(None, client.get('b'))

  def testDeleteMultiWithPrefix(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('1-a', 'a'))
    self.assertTrue(client.set('1-b', 'b'))
    self.assertEquals('a', client.get('1-a'))
    self.assertEquals('b', client.get('1-b'))
    self.assertTrue(client.delete_multi(['a', 'b'], key_prefix='1-'))
    self.assertEquals(None, client.get('1-a'))
    self.assertEquals(None, client.get('1-b'))

  def testAdd(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.add('a', 'a'))
    self.assertEquals('a', client.get('a'))
    self.assertFalse(client.add('a', 'b'))
    self.assertEquals('a', client.get('a'))

  def testAddHasNotExpired(self):
    client_one = self._client()
    client_one.flush_all()
    self.assertTrue(client_one.add('a', 'a', time=20))
    self.assertEquals('a', client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(10))
    self.assertFalse(client_two.add('a', 'b'))
    self.assertEquals('a', client_two.get('a'))

  def testAddHasExpired(self):
    client_one = self._client()
    self.assertTrue(client_one.flush_all())
    self.assertTrue(client_one.add('a', 'a', time=10))
    self.assertEquals('a', client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(20))
    self.assertTrue(client_two.add('a', 'b'))
    self.assertEquals('b', client_two.get('a'))

  def testAddMulti(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertEquals([], client.add_multi({'a': 'a', 'b': 'b'}))
    self.assertEquals('a', client.get('a'))
    self.assertEquals('b', client.get('b'))

  def testAddMultiOneFails(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.add('a', 'a', time=10))
    self.assertEquals('a', client.get('a'))
    self.assertEquals(['a'], client.add_multi({'a': 'b', 'b': 'b'}))
    self.assertEquals('a', client.get('a'))
    self.assertEquals('b', client.get('b'))

  def testReplace(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertEquals('a', client.get('a'))
    self.assertTrue(client.replace('a', 'b'))
    self.assertEquals('b', client.get('a'))

  def testReplaceFails(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertFalse(client.replace('a', 'b'))
    self.assertEquals(None, client.get('a'))

  def testReplaceMulti(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertTrue(client.set('b', 'b'))
    self.assertEquals('a', client.get('a'))
    self.assertEquals('b', client.get('b'))
    self.assertEquals([], client.replace_multi({'a': 'b', 'b': 'c'}))
    self.assertEquals('b', client.get('a'))
    self.assertEquals('c', client.get('b'))

  def testReplaceMultiOneFails(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertEquals('a', client.get('a'))
    self.assertEquals(['b'], client.replace_multi({'a': 'b', 'b': 'c'}))
    self.assertEquals('b', client.get('a'))
    self.assertEquals(None, client.get('b'))

  def testIncr(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 0))
    self.assertEquals(1, client.incr('a'))
    self.assertEquals(1, client.get('a'))
    self.assertEquals(11, client.incr('a', delta=10))
    self.assertEquals(11, client.get('a'))

  def testStringIncr(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', '0'))
    self.assertEquals('1', client.incr('a'))
    self.assertEquals('1', client.get('a'))
    self.assertEquals('11', client.incr('a', delta=10))
    self.assertEquals('11', client.get('a'))

  def testIncrBadValues(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertEquals(None, client.incr('a'))
    self.assertEquals(None, client.get('a'))
    self.assertTrue(client.set('a', 'a'))
    self.assertEquals(None, client.incr('a'))
    self.assertEquals('a', client.get('a'))

  def testIncrExpires(self):
    client_one = self._client()
    self.assertTrue(client_one.flush_all())
    self.assertTrue(client_one.set('a', 1, time=10))
    self.assertEquals(1, client_one.get('a'))
    self.assertEquals(2, client_one.incr('a'))
    self.assertEquals(2, client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(20))
    self.assertEquals(None, client_two.incr('a'))
    self.assertEquals(None, client_two.get('a'))

  def testDecr(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 11))
    self.assertEquals(10, client.decr('a'))
    self.assertEquals(10, client.get('a'))
    self.assertEquals(0, client.decr('a', delta=10))
    self.assertEquals(0, client.get('a'))

  def testStringDecr(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', '11'))
    self.assertEquals('10', client.decr('a'))
    self.assertEquals('10', client.get('a'))
    self.assertEquals('0', client.decr('a', delta=10))
    self.assertEquals('0', client.get('a'))

  def testFlushAll(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertTrue(client.set('a', 'a'))
    self.assertEquals('a', client.get('a'))
    self.assertTrue(client.set('a', '1-a', namespace='1'))
    self.assertEquals('1-a', client.get('a', namespace='1'))

  def testDefaultExpiresIn(self):
    client_one = self._client(default_time=10)
    self.assertTrue(client_one.flush_all())
    self.assertTrue(client_one.set('a', 'a'))
    self.assertEquals('a', client_one.get('a'))
    client_two = self._client(gettime=test_utils.Time(20))
    self.assertEquals(None, client_two.get('a'))
    self.assertEquals(None, client_one.get('a'))

  def testGetStats(self):
    client = self._client()
    self.assertTrue(client.flush_all())
    self.assertEquals(0, client.get_stats()['items'])
    self.assertTrue(client.set('a', '0'))
    self.assertTrue(client.set('a', 'kittens'))
    self.assertEquals(1, client.get_stats()['items'])
    self.assertTrue(client.replace('a', 'a'))
    self.assertEquals(1, client.get_stats()['items'])
    self.assertTrue(client.delete('a'))
    self.assertEquals(0, client.get_stats()['items'])
    self.assertTrue(client.add('a', 'a'))
    self.assertFalse(client.add('a', 'kittens'))
    self.assertEquals(1, client.get_stats()['items'])
    self.assertEquals('a', client.get('a'))
    self.assertEquals(None, client.get('b'))
    self.assertEquals(1, client.get_stats()['hits'])
    self.assertEquals(1, client.get_stats()['misses'])
    self.assertEquals('a', client.get('a'))
    self.assertEquals(None, client.get('b'))
    self.assertEquals(2, client.get_stats()['hits'])
    self.assertEquals(2, client.get_stats()['misses'])

if __name__ == '__main__':
  unittest.main()
