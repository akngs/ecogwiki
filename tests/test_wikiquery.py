# -*- coding: utf-8 -*-
import unittest
from search import parse_wikiquery
from google.appengine.ext import testbed


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_simplist_expression(self):
        self.assertEqual([['title', 'A'], ['title']],
                         parse_wikiquery('title:"A" > title'))
        self.assertEqual([['title', 'A'], ['title']],
                         parse_wikiquery('title:"A"'))
        self.assertEqual([['title', 'A'], ['title']],
                         parse_wikiquery('"A"'))

    def test_logical_expression(self):
        self.assertEqual([[['title', 'A'], '*', ['title', 'B']], ['title']],
                         parse_wikiquery('"A" * "B"'))
        self.assertEqual([[['title', 'A'], '+', ['title', 'B']], ['title']],
                         parse_wikiquery('"A" + "B"'))
        self.assertEqual([[['title', 'A'], '+', [['title', 'B'], '*', ['title', 'C']]], ['title']],
                         parse_wikiquery('"A" + "B" * "C"'))
        self.assertEqual([[[['title', 'A'], '+', ['title', 'B']], '*', ['title', 'C']], ['title']],
                         parse_wikiquery('("A" + "B") * "C"'))

    def test_attr_expression(self):
        self.assertEqual([['title', 'A'], ['title', 'prop.author']],
                         parse_wikiquery('title:"A" > title, prop.author'))
