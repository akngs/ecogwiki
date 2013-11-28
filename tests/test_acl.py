# -*- coding: utf-8 -*-
import unittest
from models import WikiPage
from google.appengine.api import users
from google.appengine.ext import testbed


class DefaultAclTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

        self.page = WikiPage.get_by_title(u'Hello')
        self.page.update_content(u'Hello', 0, '')
        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")

    def tearDown(self):
        self.testbed.deactivate()

    def test_read_all_write_login(self):
        default = {'read': ['all'], 'write': ['login']}
        self.assertEqual(True, self.page.can_read(None, default))
        self.assertEqual(False, self.page.can_write(None, default))
        self.assertEqual(True, self.page.can_read(self.user1, default))
        self.assertEqual(True, self.page.can_write(self.user1, default))

    def test_read_login_write_login(self):
        default = {'read': ['login'], 'write': ['login']}
        self.assertEqual(False, self.page.can_read(None, default))
        self.assertEqual(False, self.page.can_write(None, default))
        self.assertEqual(True, self.page.can_read(self.user1, default))
        self.assertEqual(True, self.page.can_write(self.user1, default))

    def test_read_all_write_all(self):
        default = {'read': ['all'], 'write': ['all']}
        self.assertEqual(True, self.page.can_read(None, default))
        self.assertEqual(True, self.page.can_write(None, default))
        self.assertEqual(True, self.page.can_read(self.user1, default))
        self.assertEqual(True, self.page.can_write(self.user1, default))

    def test_specific_user(self):
        default = {'read': ['all'], 'write': ['user1@example.com']}
        self.assertEqual(True, self.page.can_read(None, default))
        self.assertEqual(False, self.page.can_write(None, default))
        self.assertEqual(True, self.page.can_read(self.user1, default))
        self.assertEqual(True, self.page.can_write(self.user1, default))
        self.assertEqual(True, self.page.can_read(self.user2, default))
        self.assertEqual(False, self.page.can_write(self.user2, default))


class PageLevelAclTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")
        self.default = {'read': ['all'], 'write': ['login']}
        self.page = WikiPage.get_by_title(u'Hello')

    def tearDown(self):
        self.testbed.deactivate()

    def test_default(self):
        self.page.update_content(u'Hello', 0, '')
        self.assertEqual(True, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_stricter_read(self):
        self.page.update_content(u'.read login\nHello', 0, '')
        self.assertEqual(False, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_looser_write(self):
        self.page.update_content(u'.write all\nHello', 0, '')
        self.assertEqual(True, self.page.can_read(None, self.default))
        self.assertEqual(True, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))


class InconsistantAclTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")
        self.default = {'read': ['all'], 'write': ['login']}
        self.page = WikiPage.get_by_title(u'Hello')

    def tearDown(self):
        self.testbed.deactivate()

    def test_read_login_write_all(self):
        self.page.update_content(u'.read login\n.write all\nHello', 0, '')
        self.assertEqual(True, self.page.can_read(None, self.default))
        self.assertEqual(True, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_read_specified_user_write_login(self):
        self.page.update_content(u'.read user2@example.com\n.write login\nHello', 0, '')
        self.assertEqual(False, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))
        self.assertEqual(True, self.page.can_read(self.user2, self.default))
        self.assertEqual(True, self.page.can_write(self.user2, self.default))
