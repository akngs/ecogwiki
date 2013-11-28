# -*- coding: utf-8 -*-
import unittest
from search import parse_wikiquery
from google.appengine.ext import testbed


class WikiqueryParserTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_simplist_expression(self):
        self.assertEqual([['name', 'A'], ['name']],
                         parse_wikiquery('name:"A" > name'))
        self.assertEqual([['name', 'A'], ['name']],
                         parse_wikiquery('name:"A"'))
        self.assertEqual([['name', 'A'], ['name']],
                         parse_wikiquery('"A"'))

    def test_logical_expression(self):
        self.assertEqual([[['name', 'A'], '*', ['name', 'B']], ['name']],
                         parse_wikiquery('"A" * "B"'))
        self.assertEqual([[['name', 'A'], '+', ['name', 'B']], ['name']],
                         parse_wikiquery('"A" + "B"'))
        self.assertEqual([[['name', 'A'], '+', [['name', 'B'], '*', ['name', 'C']]], ['name']],
                         parse_wikiquery('"A" + "B" * "C"'))
        self.assertEqual([[[['name', 'A'], '+', ['name', 'B']], '*', ['name', 'C']], ['name']],
                         parse_wikiquery('("A" + "B") * "C"'))

    def test_attr_expression(self):
        self.assertEqual([['name', 'A'], ['name', 'author']],
                         parse_wikiquery('name:"A" > name, author'))
