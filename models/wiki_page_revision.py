# -*- coding: utf-8 -*-
from google.appengine.ext import ndb
from models import PageOperationMixin


class WikiPageRevision(ndb.Model, PageOperationMixin):
    title = ndb.StringProperty()
    body = ndb.TextProperty()
    revision = ndb.IntegerProperty()
    comment = ndb.StringProperty()
    modifier = ndb.UserProperty()
    acl_read = ndb.StringProperty()
    acl_write = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()

    @property
    def absolute_url(self):
        return u'/%s?rev=%d' % (PageOperationMixin.title_to_path(self.title), int(self.revision))

    @property
    def is_old_revision(self):
        return True

    @property
    def updated_at(self):
        return self.created_at

    @property
    def inlinks(self):
        return {}

    @property
    def outlinks(self):
        return {}

    @property
    def related_links(self):
        return {}

    @property
    def older_title(self):
        return None

    @property
    def newer_title(self):
        return None
