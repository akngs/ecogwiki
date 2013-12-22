# -*- coding: utf-8 -*-
from google.appengine.ext import ndb


class SchemaDataIndex(ndb.Model):
    title = ndb.StringProperty()
    name = ndb.StringProperty()
    value = ndb.StringProperty()
