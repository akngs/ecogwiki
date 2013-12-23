# -*- coding: utf-8 -*-
from models import WikiPage
from tests import AppEngineTestCase
from google.appengine.api import users


class DefaultAclTest(AppEngineTestCase):
    def setUp(self):
        super(DefaultAclTest, self).setUp()

        self.page = WikiPage.get_by_title(u'Hello')
        self.page.update_content(u'Hello', 0)
        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")

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


class PageLevelAclTest(AppEngineTestCase):
    def setUp(self):
        super(PageLevelAclTest, self).setUp()

        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")
        self.default = {'read': ['all'], 'write': ['login']}
        self.page = WikiPage.get_by_title(u'Hello')

    def test_default(self):
        self.page.update_content(u'Hello', 0)
        self.assertEqual(True, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_stricter_read(self):
        self.page.update_content(u'.read login\nHello', 0)
        self.assertEqual(False, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_looser_write(self):
        self.page.update_content(u'.write all\nHello', 0)
        self.assertEqual(True, self.page.can_read(None, self.default))
        self.assertEqual(True, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_different_read_and_write(self):
        self.page.update_content(u'.write user1@example.com\n.read user2@example.com\nHello', 0)
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(False, self.page.can_read(None, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(False, self.page.can_write(self.user2, self.default))
        self.assertEqual(True, self.page.can_read(self.user2, self.default))


class InconsistantAclTest(AppEngineTestCase):
    def setUp(self):
        super(InconsistantAclTest, self).setUp()

        self.user1 = users.User("user1@example.com")
        self.user2 = users.User("user2@example.com")
        self.default = {'read': ['all'], 'write': ['login']}
        self.page = WikiPage.get_by_title(u'Hello')

    def test_read_login_write_all(self):
        self.page.update_content(u'.read login\n.write all\nHello', 0)
        self.assertEqual(False, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(True, self.page.can_read(self.user1, self.default))
        self.assertEqual(True, self.page.can_write(self.user1, self.default))

    def test_read_specified_user_write_login(self):
        self.page.update_content(u'.read user2@example.com\n.write login\nHello', 0)
        self.assertEqual(False, self.page.can_read(None, self.default))
        self.assertEqual(False, self.page.can_write(None, self.default))
        self.assertEqual(False, self.page.can_read(self.user1, self.default))
        self.assertEqual(False, self.page.can_write(self.user1, self.default))
        self.assertEqual(True, self.page.can_read(self.user2, self.default))
        self.assertEqual(True, self.page.can_write(self.user2, self.default))
