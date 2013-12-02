# -*- coding: utf-8 -*-
import cache
from models import WikiPage
import unittest2 as unittest
from google.appengine.api import users
from search import parse_wikiquery as p
from google.appengine.ext import testbed


class WikiqueryParserTest(unittest.TestCase):
    def test_simplist_expression(self):
        self.assertEqual([['name', 'A'], ['name']],
                         p('name:"A" > name'))
        self.assertEqual([['name', 'A'], ['name']],
                         p('name:"A"'))
        self.assertEqual([['name', 'A'], ['name']],
                         p('"A"'))

    def test_logical_expression(self):
        self.assertEqual([[['name', 'A'], '*', ['name', 'B']], ['name']],
                         p('"A" * "B"'))
        self.assertEqual([[['name', 'A'], '+', ['name', 'B']], ['name']],
                         p('"A" + "B"'))
        self.assertEqual([[['name', 'A'], '+', [['name', 'B'], '*', ['name', 'C']]], ['name']],
                         p('"A" + "B" * "C"'))
        self.assertEqual([[[['name', 'A'], '+', ['name', 'B']], '*', ['name', 'C']], ['name']],
                         p('("A" + "B") * "C"'))

    def test_attr_expression(self):
        self.assertEqual([['name', 'A'], ['name', 'author']],
                         p('name:"A" > name, author'))


#class WikiqueryNormalizerTest(unittest.TestCase):
#    def test_ordering(self):
#        self.assertEqual(p('"A" * "B"'), p('"B" * "A"'))
#        self.assertEqual(p('"A" * ("B" + "C")'), p('("C" + "B") * "A"'))
#
#    def test_parentheses(self):
#        self.assertEqual(p('"A"'), p('("A")'))
#        self.assertEqual(p('"A" + "B"'), p('("A" + "B")'))
#
#        self.assertEqual(p('"A" + "B" + "C"'), p('("A" + "B") + "C"'))
#        self.assertEqual(p('"A" + "B" + "C"'), p('"A" + ("B" + "C")'))
#
#        self.assertEqual(p('"A" * "B" * "C"'), p('("A" * "B") * "C"'))
#        self.assertEqual(p('"A" * "B" * "C"'), p('"A" * ("B" * "C")'))
#
#        self.assertNotEqual(p('"A" + "B" * "C"'), p('("A" + "B") * "C"'))
#        self.assertNotEqual(p('"A" * "B" * "C"'), p('("A" * "B") * "C"'))
#
#    def test_remove_dup(self):
#        self.assertEqual(p('"A" * "B"'), p('"A" * "B" * "A"'))
#        self.assertEqual(p('"A" + "B"'), p('"A" + "B" + "A"'))
#        self.assertEqual(p('"A" + "B"'), p('("A" + "B") * ("A" + "B")'))
#
#    def test_elimination(self):
#        # (A * B) + A == A
#        self.assertEqual(p('"A"'), p('"A" * "B" + "A"'))
#
#        # A + (B * (C * A)) == A
#        self.assertEqual(p('"A"'), p('"A" + ("B" * ("C" * "A"))'))
#
#        # A * (A + B) = A
#        self.assertEqual(p('"A"'), p('"A" * ("A" + "B")'))
#
#        # A * C * (A + B + C + D) = A * C
#        self.assertEqual(p('"A" * "C"'), p('"A" * "C" * ("A" + "B" + "C" + "D")'))


class WikiqueryEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        cache.prc.flush_all()

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


class WikiqueryAclEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        cache.prc.flush_all()

        WikiPage.get_by_title(u'A').update_content(u'.schema Book\n.read all\nHello', 0, u'')
        WikiPage.get_by_title(u'B').update_content(u'.schema Book\n.read a@x.com\nThere', 0, u'')
        for p in WikiPage.query().fetch():
            p.rebuild_data_index()

    def tearDown(self):
        self.testbed.deactivate()

    def test_anonymous(self):
        self.assertEqual({u'name': u'A'},
                         WikiPage.wikiquery(u'schema:"Book"', None))

    def test_user_with_no_permission(self):
        user = users.User('a@y.com')
        self.assertEqual({u'name': u'A'},
                         WikiPage.wikiquery(u'schema:"Book"', user))

    def test_user_with_permission(self):
        user = users.User('a@x.com')
        self.assertEqual([{u'name': u'A'}, {u'name': u'B'}],
                         WikiPage.wikiquery(u'schema:"Book"', user))
