# -*- coding: utf-8 -*-
import os
from views import WikiPageHandler
from models import is_admin_user
import unittest2 as unittest
from google.appengine.ext import testbed


def user_login(email, user_id, is_admin=False):
    os.environ['USER_EMAIL'] = email or ''
    os.environ['USER_ID'] = user_id or ''
    os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'


def user_logout():
    user_login(None, None)


def get_current_user():
    return WikiPageHandler._get_cur_user()


def current_user_is_admin():
    user = get_current_user()
    return is_admin_user(user)


class CurrentUserTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.oauth_stub = OAuthStub(self.testbed, logout=True)

    def tearDown(self):
        self.testbed.deactivate()
        user_logout()

    def test_none_on_logout(self):
        user = get_current_user()
        self.assertIsNone(user)

    def test_users_first(self):
        user_login('ak@gmail.com', 'ak')
        self.oauth_stub.login('jh@gmail.com', 'jh')
        self.assertEquals(get_current_user().email(), 'ak@gmail.com')

    def test_oauth_only_when_user_is_not_logged_in(self):
        self.oauth_stub.login('jh@gmail.com', 'jh')
        self.assertEquals(get_current_user().email(), 'jh@gmail.com')


class AdminUserTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.oauth_stub = OAuthStub(self.testbed, logout=True)

    def tearDown(self):
        self.testbed.deactivate()
        user_logout()

    def test_false_when_logged_out(self):
        self.assertFalse(current_user_is_admin())

    def test_user_login(self):
        user_login('ak@gmail.com', 'ah', is_admin=True)
        self.assertTrue(current_user_is_admin())

        user_login('jh@gmail.com', 'jh', is_admin=False)
        self.assertFalse(current_user_is_admin())

    def test_oauth_login(self):
        self.oauth_stub.login('ak@gmail.com', 'ah', is_admin=True)
        self.assertTrue(current_user_is_admin())

        self.oauth_stub.login('jh@gmail.com', 'jh', is_admin=False)
        self.assertFalse(current_user_is_admin())


class OAuthStub(object):
    def __init__(self, testbed_obj, logout=True):
        self.user_stub = testbed_obj._test_stub_map.GetStub(testbed.USER_SERVICE_NAME)
        if logout:
            self.logout()

    def login(self, email, user_id, is_admin=False):
        """
            UserServiceStub.SetOAuthUser(
                             email=_OAUTH_EMAIL,
                             domain=_OAUTH_AUTH_DOMAIN,
                             user_id=_OAUTH_USER_ID,
                             is_admin=False,
                             scopes=None,
                             client_id=_OAUTH_CLIENT_ID)
        """
        # no OAuth login
        self.user_stub.SetOAuthUser(email=email, user_id=user_id, is_admin=is_admin)
        os.environ['OAUTH_EMAIL'] = email or ''
        os.environ['OAUTH_USER_ID'] = user_id or ''
        os.environ['OAUTH_IS_ADMIN'] = '1' if is_admin else '0'

    def logout(self):
        self.login(email=None, user_id=None)

