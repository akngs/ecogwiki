#!/usr/bin/python2.5
#
# Test the cache implementations.
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

import logging
import memory_test
import os
import os.path
import unittest
import sys
import test_utils

def suite():
  suite = unittest.TestSuite()
  suite.addTests(memory_test.suite())
  try:
    test_utils.init_appengine()
    import memcache_test
    suite.addTests(memcache_test.suite())
    import datastore_test
    suite.addTests(datastore_test.suite())
    import layered_test
    suite.addTests(layered_test.suite())
    try:
      test_utils.init_httplib2()
      import httplib2_test
      suite.addTests(httplib2_test.suite())
    except ImportError, e:
      raise e
  except Exception, e:
    logging.warning(e)
    logging.warning('memcache, datastore, and layered tests disabled.')
  return suite

if __name__ == '__main__':
  unittest.TextTestRunner(verbosity=2).run(suite())
