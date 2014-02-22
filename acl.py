import main


from google.appengine.api import users
from google.appengine.api import oauth


class ACL(object):
    def __init__(self, default_acl, read, write):
        self._default_acl = default_acl
        self._read = self._to_list(read)
        self._write = self._to_list(write)

    def can_read(self, user, acl_r=None, acl_w=None):
        default_acl = self._default_acl or main.DEFAULT_CONFIG['service']['default_permissions']
        acl_r = acl_r or self._read or default_acl['read'] or []
        acl_w = acl_w or self._write or default_acl['write'] or []

        if u'all' in acl_r or len(acl_r) == 0:
            return True
        elif user is not None and u'login' in acl_r:
            return True
        elif user is not None and (user.email() in acl_r or user.email() in acl_w):
            return True
        elif self._is_admin(user):
            return True
        else:
            return False

    def can_write(self, user, acl_r=None, acl_w=None):
        default_acl = self._default_acl or main.DEFAULT_CONFIG['service']['default_permissions']
        acl_w = acl_w or self._write or default_acl['write'] or []

        if (not self.can_read(user, acl_r, acl_w)) and (user is None or user.email() not in acl_w):
            return False
        elif 'all' in acl_w:
            return True
        elif (len(acl_w) == 0 or u'login' in acl_w) and user is not None:
            return True
        elif user is not None and user.email() in acl_w:
            return True
        elif self._is_admin(user):
            return True
        else:
            return False

    def _to_list(self, acl):
        if type(acl) in [list, tuple]:
            return acl
        if acl is None or len(acl) == 0:
            return []
        else:
            return [token.strip() for token in acl.split(',')]

    def _is_admin(self, user):
        if not user:
            return False

        if users.is_current_user_admin():
            return True

        try:
            if oauth.is_current_user_admin():
                return True
        except oauth.OAuthRequestError:
            pass

        return False
