# -*- coding: utf-8 -*-
import schema
import unittest


class SchemaTest(unittest.TestCase):
    def test_humane_itemtype(self):
        self.assertEqual('Book', schema.humane_item('Book'))
        self.assertEqual('Creative work', schema.humane_item('CreativeWork'))

    def test_humane_property(self):
        self.assertEqual('Publications',
                         schema.humane_property('Book', 'datePublished', True))
        self.assertEqual('Published date',
                         schema.humane_property('Book', 'datePublished', False))

    def test_itemtype_path(self):
        self.assertEqual('Thing/',
                         schema.get_itemtype_path('Thing'))
        self.assertEqual('Thing/CreativeWork/Article/',
                         schema.get_itemtype_path('Article'))

    def test_every_itemtype_should_have_a_parent_except_for_root(self):
        for item in schema.SUPPORTED_SCHEMA.keys():
            self.assertEqual('Thing/', schema.get_itemtype_path(item)[:6])
