# -*- coding: utf-8 -*-
import cache
import unittest2 as unittest
from google.appengine.ext import testbed


class AppEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        cache.prc.flush_all()

    def tearDown(self):
        self.testbed.deactivate()
