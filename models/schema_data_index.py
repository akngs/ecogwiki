# -*- coding: utf-8 -*-
import logging
from google.appengine.ext import ndb


logging.getLogger().setLevel(logging.DEBUG)

class SchemaDataIndex(ndb.Model):
    title = ndb.StringProperty()
    name = ndb.StringProperty()
    value = ndb.StringProperty()

