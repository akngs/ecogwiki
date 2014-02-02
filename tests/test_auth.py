# -*- coding: utf-8 -*-
import os
from tests import AppEngineTestCase
from google.appengine.ext import testbed


class CurrentUserTest(AppEngineTestCase):
    def setUp(self):
        super(CurrentUserTest, self).setUp()
        self.oauth_stub = OAuthStub(self.testbed)

    def test_none_on_logout(self):
        self.assertIsNone(self.get_cur_user())

    def test_users_first(self):
        self.login('ak@gmail.com', 'ak')
        self.oauth_stub.login('jh@gmail.com', 'jh')
        self.assertEqual(self.get_cur_user().email(), 'ak@gmail.com')

    def test_oauth_only_when_user_is_not_logged_in(self):
        self.oauth_stub.login('jh@gmail.com', 'jh')
        self.assertEqual(self.get_cur_user().email(), 'jh@gmail.com')


class AdminUserTest(AppEngineTestCase):
    def setUp(self):
        super(AdminUserTest, self).setUp()
        self.oauth_stub = OAuthStub(self.testbed)

    def test_false_when_logged_out(self):
        self.assertFalse(self.is_admin())

    def test_user_login(self):
        self.login('ak@gmail.com', 'ah', is_admin=True)
        self.assertTrue(self.is_admin())

        self.login('jh@gmail.com', 'jh')
        self.assertFalse(self.is_admin())

    def test_oauth_login(self):
        self.oauth_stub.login('ak@gmail.com', 'ah', is_admin=True)
        self.assertTrue(self.is_admin())

        self.oauth_stub.login('jh@gmail.com', 'jh')
        self.assertFalse(self.is_admin())


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
