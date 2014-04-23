from google.appengine.ext import ndb
from datetime import datetime


class UserPreferences(ndb.Model):
    user = ndb.UserProperty()
    userpage_title = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()

    @classmethod
    def get_by_user(cls, user):
        keyid = ndb.Key(cls, user.email()).string_id()
        prefs = cls.get_by_id(keyid)
        if prefs is None:
            prefs = cls(id=keyid)
            prefs.user = user
            prefs.created_at = datetime.now()
        return prefs
