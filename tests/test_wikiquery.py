# -*- coding: utf-8 -*-
import unittest
from models import WikiPage
from google.appengine.ext import testbed
from search import parse_wikiquery


class WikiqueryParserTest(unittest.TestCase):
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


class WikiqueryEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

        WikiPage.get_by_title(u'The Mind\'s I').update_content(u'.schema Book\n[[author::Daniel Dennett]] and [[author::Douglas Hofstadter]]\n[[datePublished::1982]]', 0, u'')
        WikiPage.get_by_title(u'GEB').update_content(u'.schema Book\n{{author::Douglas Hofstadter}}\n[[datePublished::1979]]', 0, u'')
        WikiPage.get_by_title(u'Douglas Hofstadter').update_content(u'.schema Person', 0, u'')
        for p in WikiPage.query().fetch():
            p.rebuild_data_index()

    def tearDown(self):
        self.testbed.deactivate()

    def test_by_name(self):
        self.assertEqual({u'name': u'GEB'},
                         WikiPage.wikiquery(u'"GEB"'))

    def test_by_schema(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Thing/CreativeWork/Book/"'))

    def test_by_abbr_schema(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Book"'))

    def test_by_attr(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'author:"Douglas Hofstadter"'))

    def test_specifying_attr(self):
        self.assertEqual({u'author': u'Douglas Hofstadter'},
                         WikiPage.wikiquery(u'"GEB" > author'))
        self.assertEqual({u'author': u'Douglas Hofstadter', u'name': u'GEB', u'datePublished': u'1979'},
                         WikiPage.wikiquery(u'"GEB" > name, author, datePublished'))

    def test_logical_operations(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'"GEB" + "The Mind\'s I"'))
        self.assertEqual({u'name': u'The Mind\'s I'},
                         WikiPage.wikiquery(u'schema:"Book" * author:"Douglas Hofstadter" * author:"Daniel Dennett"'))
        self.assertEqual([{'name': u"The Mind's I"}, {'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Book" + author:"Douglas Hofstadter" * author:"Daniel Dennett"'))

    def test_complex(self):
        self.assertEqual([{u'name': u'The Mind\'s I', u'author': [u'Daniel Dennett', u'Douglas Hofstadter']},
                          {u'author': u'Douglas Hofstadter', u'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Thing/CreativeWork/Book/" > name, author'))
