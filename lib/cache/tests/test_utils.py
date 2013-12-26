#!/usr/bin/python2.5
#
# Utilities for setting up unit tests.
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
import os
import os.path
import sys
import tempfile
import time

appengine_initialized = False
httplib2_initialized = False

TEST_APP_ID = 'python-cache-test'

def init_appengine():
  global appengine_initialized
  if appengine_initialized:
    return

  try:
    dev_appserver = os.environ['APPSERVER']
  except KeyError, e:
    logging.warning(
      'Please set the APPSERVER env variable to point to dev_appserver.py')
    raise e

  dev_appserver_path = os.path.realpath(dev_appserver)
  dev_appserver_dir = os.path.dirname(dev_appserver_path)
  sys.path.append(dev_appserver_dir)

  # Paths taken from dev_appserver.py EXTRA_LIBS
  sys.path.append(os.path.join(dev_appserver_dir, 'lib', 'antlr3'))
  sys.path.append(os.path.join(dev_appserver_dir, 'lib', 'django'))
  sys.path.append(os.path.join(dev_appserver_dir, 'lib', 'webob'))
  sys.path.append(os.path.join(dev_appserver_dir, 'lib', 'yaml', 'lib'))

  import google.appengine.api.apiproxy_stub_map as apiproxy_stub_map
  import google.appengine.api.memcache.memcache_stub as memcache_stub
  import google.appengine.api.datastore_file_stub as datastore_file_stub

  # Register the service stub on test initialization
  apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
  memcache_service_stub = memcache_stub.MemcacheServiceStub()
  memcache_service_stub._gettime = Time()  # Share a single clock
  apiproxy_stub_map.apiproxy.RegisterStub('memcache', memcache_service_stub)
  temp_datastore_path = tempfile.mktemp()
  os.environ['APPLICATION_ID'] = TEST_APP_ID
  datastore_file_stub = datastore_file_stub.DatastoreFileStub(
    TEST_APP_ID,
    temp_datastore_path,
    require_indexes=False,
    trusted=False
    )
  apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', datastore_file_stub)
  logging.info('Appengine successfully initialized')
  appengine_initialized = True

def init_httplib2():
  global httplib2_initialized
  if httplib2_initialized:
    return
  try:
    import httplib2
  except ImportError, e:
    logging.warning('Please install httplib2 on your path.')
    raise e
  httplib2_initialized = True

class Time(object):
  """A function-like object that returns a time."""
  def __init__(self, delta=0):
    self.adjust(delta)
    
  def __call__(self):
    """Return the time."""
    return self._time

  def update(self, now):
    """Set the time to now."""
    self._time = now

  def adjust(self, delta):
    """Set the time delta seconds into the past or future."""
    self._time = time.time() + delta

  def reset(self):
    """Set the time to the current time."""
    self._time = time.time()

