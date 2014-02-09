# -*- coding: utf-8 -*-
import schema
from google.appengine.ext import ndb


class SchemaDataIndex(ndb.Model):
    title = ndb.StringProperty()
    name = ndb.StringProperty()
    value = ndb.StringProperty()

    @classmethod
    def rebuild_index(cls, title, data):
        # delete
        keys = [i.key for i in cls.query_by_title(title).fetch()]
        ndb.delete_multi(keys)

        # insert
        entities = [cls(title=title, name=name, value=v.pvalue if isinstance(v, schema.Property) else v)
                    for name, v in cls.data_as_pairs(data)
                    if not isinstance(v, schema.Property) or v.should_index()]
        ndb.put_multi(entities)

    @classmethod
    def update_index(cls, title, old_data, new_data):
        old_pairs = cls.data_as_pairs(old_data)
        new_pairs = cls.data_as_pairs(new_data)

        deletes = old_pairs.difference(new_pairs)
        inserts = new_pairs.difference(old_pairs)

        # delete
        queries = [cls.query(cls.title == title, cls.name == name, cls.value == (v.pvalue if isinstance(v, schema.Property) else v))
                   for name, v in deletes]
        entities = reduce(lambda a, b: a + b, [q.fetch() for q in queries], [])
        keys = [e.key for e in entities]
        if len(keys) > 0:
            ndb.delete_multi(keys)

        # insert
        entities = [cls(title=title, name=name, value=v.pvalue if isinstance(v, schema.Property) else v)
                    for name, v in inserts
                    if not isinstance(v, schema.Property) or v.should_index()]

        if len(entities) > 0:
            ndb.put_multi(entities)

    @classmethod
    def query_by_title(cls, title):
        return cls.query(cls.title == title)

    @classmethod
    def query_titles(cls, name, value):
        return [i.title for i in cls.query(cls.name == name, cls.value == value)]

    @classmethod
    def has_match(cls, title, name, value):
        return cls.query(cls.title == title, cls.name == name, cls.value == value).count() > 0

    @staticmethod
    def data_as_pairs(data):
        pairs = set()
        for key, value in data.items():
            if type(value) == list:
                pairs.update((key, v) for v in value)
            else:
                pairs.add((key, value))
        return pairs
