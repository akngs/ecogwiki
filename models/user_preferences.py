from google.appengine.ext import ndb
from datetime import datetime


class UserPreferences(ndb.Model):
    user = ndb.UserProperty()
    userpage_title = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()

    @classmethod
    def save(cls, user, userpage_title):
        keyid = ndb.Key(cls, user.email()).string_id()
        preferences = cls.get_by_id(keyid)
        if preferences is None:
            preferences = cls(id=keyid)
            preferences.user = user
            preferences.created_at = datetime.now()

        preferences.userpage_title = userpage_title
        preferences.put()
        return preferences

    @classmethod
    def get_by_user(cls, user):
        keyid = ndb.Key(cls, user.email()).string_id()
        prefs = cls.get_by_id(keyid)
        if prefs is None:
            prefs = cls(id=keyid)
            prefs.user = user
            prefs.created_at = datetime.now()
        return prefs
