# -*- coding: utf-8 -*-
import os
from acl import ACL
import unittest2 as unittest
from tests import AppEngineTestCase
from google.appengine.api import users
from google.appengine.ext import testbed


class AclTestCase(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()

    def tearDown(self):
        self.testbed.deactivate()
        self.logout()

    def login(self, email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    def logout(self):
        self.login(None, None)

    def assertAcl(self, readable, writable, acl_r, acl_w, user, default_permission):
        self.assertEqual(readable, ACL(default_permission, acl_r, acl_w).can_read(user))
        self.assertEqual(writable, ACL(default_permission, acl_r, acl_w).can_write(user))


class SystemWideAclTest(AclTestCase):
    def setUp(self):
        super(SystemWideAclTest, self).setUp()

        self.login('user1@example.com', 'user1')
        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")

    def test_read_all_write_login(self):
        default = {'read': ['all'], 'write': ['login']}
        self.assertAcl(True, False, [], [], None, default)
        self.assertAcl(True, True, [], [], self.user1, default)

    def test_read_login_write_login(self):
        default = {'read': ['login'], 'write': ['login']}
        self.assertAcl(False, False, [], [], None, default)
        self.assertAcl(True, True, [], [], self.user1, default)

    def test_read_all_write_all(self):
        default = {'read': ['all'], 'write': ['all']}
        self.assertAcl(True, True, [], [], None, default)
        self.assertAcl(True, True, [], [], self.user1, default)

    def test_specific_user(self):
        default = {'read': ['all'], 'write': ['user1@example.com']}
        self.assertAcl(True, False, [], [], None, default)
        self.assertAcl(True, True, [], [], self.user1, default)
        self.assertAcl(True, False, [], [], self.user2, default)


class PageLevelAclTest(AclTestCase):
    def setUp(self):
        super(PageLevelAclTest, self).setUp()

        self.login('user1@example.com', 'user1')
        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")
        self.default = {'read': ['all'], 'write': ['login']}

    def test_default(self):
        self.assertAcl(True, False, [], [], None, self.default)
        self.assertAcl(True, True, [], [], self.user1, self.default)

    def test_stricter_read(self):
        self.assertAcl(False, False, ['login'], [], None, self.default)
        self.assertAcl(True, True, ['login'], [], self.user1, self.default)

    def test_looser_write(self):
        self.assertAcl(True, True, [], ['all'], None, self.default)
        self.assertAcl(True, True, [], ['all'], self.user1, self.default)

    def test_different_read_and_write(self):
        self.assertAcl(False, False, ['user2@example.com'], ['user1@example.com'], None, self.default)
        self.assertAcl(True, True, ['user2@example.com'], ['user1@example.com'], self.user1, self.default)
        self.assertAcl(True, False, ['user2@example.com'], ['user1@example.com'], self.user2, self.default)

    def test_read_login_write_all(self):
        self.assertAcl(False, False, ['login'], ['all'], None, self.default)
        self.assertAcl(True, True, ['login'], ['all'], self.user1, self.default)

    def test_read_specified_user_write_login(self):
        self.assertAcl(False, False, ['user1@example.com'], ['login'], None, self.default)
        self.assertAcl(True, True, ['user1@example.com'], ['login'], self.user1, self.default)
        self.assertAcl(False, False, ['user1@example.com'], ['login'], self.user2, self.default)


class AclParsingTest(AppEngineTestCase):
    def setUp(self):
        super(AclParsingTest, self).setUp()
        self.login('user1@example.com', 'user1')

    def test_empty(self):
        page = self.update_page(u'Hello')
        self.assertEqual(u'', page.acl_read)
        self.assertEqual(u'', page.acl_write)

    def test_read(self):
        page = self.update_page(u'.read user1@example.com')
        self.assertEqual(u'user1@example.com', page.acl_read)
        self.assertEqual(u'', page.acl_write)

    def test_write(self):
        page = self.update_page(u'.write user1@example.com')
        self.assertEqual(u'', page.acl_read)
        self.assertEqual(u'user1@example.com', page.acl_write)
