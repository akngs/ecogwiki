# -*- coding: utf-8 -*-
import os
import caching
import unittest2 as unittest
from google.appengine.ext import testbed
from models import get_cur_user, is_admin_user


class AppEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        caching.flush_all()

    def tearDown(self):
        self.testbed.deactivate()
        self.logout()

    def login(self, email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    def logout(self):
        self.login(None, None)

    def get_cur_user(self):
        return get_cur_user()

    def is_admin(self):
        return is_admin_user(self.get_cur_user())