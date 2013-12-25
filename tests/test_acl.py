# -*- coding: utf-8 -*-
from models import WikiPage
from tests import AppEngineTestCase
from google.appengine.api import users


class AclTestCase(AppEngineTestCase):
    def setUp(self):
        super(AclTestCase, self).setUp()

    def assertAcl(self, readable, writable, page, user, default_permission):
        self.assertEqual(readable, page.can_read(user, default_permission))
        self.assertEqual(writable, page.can_write(user, default_permission))


class DefaultAclTest(AclTestCase):
    def setUp(self):
        super(DefaultAclTest, self).setUp()

        self.page = WikiPage.get_by_title(u'Hello')
        self.page.update_content(u'Hello', 0)
        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")

    def test_read_all_write_login(self):
        default = {'read': ['all'], 'write': ['login']}
        self.assertAcl(True, False, self.page, None, default)
        self.assertAcl(True, True, self.page, self.user1, default)

    def test_read_login_write_login(self):
        default = {'read': ['login'], 'write': ['login']}
        self.assertAcl(False, False, self.page, None, default)
        self.assertAcl(True, True, self.page, self.user1, default)

    def test_read_all_write_all(self):
        default = {'read': ['all'], 'write': ['all']}
        self.assertAcl(True, True, self.page, None, default)
        self.assertAcl(True, True, self.page, self.user1, default)

    def test_specific_user(self):
        default = {'read': ['all'], 'write': ['user1@example.com']}
        self.assertAcl(True, False, self.page, None, default)
        self.assertAcl(True, True, self.page, self.user1, default)
        self.assertAcl(True, False, self.page, self.user2, default)


class PageLevelAclTest(AclTestCase):
    def setUp(self):
        super(PageLevelAclTest, self).setUp()

        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")
        self.default = {'read': ['all'], 'write': ['login']}
        self.page = WikiPage.get_by_title(u'Hello')

    def test_default(self):
        self.page.update_content(u'Hello', 0)
        self.assertAcl(True, False, self.page, None, self.default)
        self.assertAcl(True, True, self.page, self.user1, self.default)

    def test_stricter_read(self):
        self.page.update_content(u'.read login\nHello', 0)
        self.assertAcl(False, False, self.page, None, self.default)
        self.assertAcl(True, True, self.page, self.user1, self.default)

    def test_looser_write(self):
        self.page.update_content(u'.write all\nHello', 0)
        self.assertAcl(True, True, self.page, None, self.default)
        self.assertAcl(True, True, self.page, self.user1, self.default)

    def test_different_read_and_write(self):
        self.page.update_content(u'.write user1@example.com\n.read user2@example.com\nHello', 0)
        self.assertAcl(False, False, self.page, None, self.default)
        self.assertAcl(True, True, self.page, self.user1, self.default)
        self.assertAcl(True, False, self.page, self.user2, self.default)

    def test_read_login_write_all(self):
        self.page.update_content(u'.read login\n.write all\nHello', 0)
        self.assertAcl(False, False, self.page, None, self.default)
        self.assertAcl(True, True, self.page, self.user1, self.default)

    def test_read_specified_user_write_login(self):
        self.page.update_content(u'.read user2@example.com\n.write login\nHello', 0)
        self.assertAcl(False, False, self.page, None, self.default)
        self.assertAcl(False, False, self.page, self.user1, self.default)
        self.assertAcl(True, True, self.page, self.user2, self.default)
