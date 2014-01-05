# -*- coding: utf-8 -*-
from models import WikiPage
import unittest2 as unittest
from tests import AppEngineTestCase
from google.appengine.api import users
from search import parse_wikiquery as p


class ParserTest(unittest.TestCase):
    def test_simplist_expression(self):
        self.assertEqual([['name', 'A'], ['name']], p('name:"A" > name'))
        self.assertEqual([['name', 'A'], ['name']], p('name:"A"'))
        self.assertEqual([['name', 'A'], ['name']], p('"A"'))

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
        self.assertEqual([['name', 'A'], ['name', 'author']], p('name:"A" > name, author'))


#class NormalizerTest(unittest.TestCase):
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


class EvaluationTest(AppEngineTestCase):
    def setUp(self):
        super(EvaluationTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

        self.update_page(u'.schema Book\n[[author::Daniel Dennett]] and [[author::Douglas Hofstadter]]\n[[datePublished::1982]]', u'The Mind\'s I')
        self.update_page(u'.schema Book\n{{author::Douglas Hofstadter}}\n[[datePublished::1979]]', u'GEB')
        self.update_page(u'.schema Person', u'Douglas Hofstadter')

    def test_by_name(self):
        self.assertEqual({u'name': u'GEB'}, WikiPage.wikiquery(u'"GEB"'))

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
        result = WikiPage.wikiquery(u'"GEB" > author')
        self.assertEqual(u'Douglas Hofstadter', result['author'].pvalue)

        result = WikiPage.wikiquery(u'"GEB" > name, author, datePublished')
        self.assertEqual(u'Douglas Hofstadter', result['author'].pvalue)
        self.assertEqual(u'GEB', result['name'].pvalue)
        self.assertEqual(u'1979', result['datePublished'].pvalue)

    def test_logical_operations(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'"GEB" + "The Mind\'s I"'))
        self.assertEqual({u'name': u'The Mind\'s I'},
                         WikiPage.wikiquery(u'schema:"Book" * author:"Douglas Hofstadter" * author:"Daniel Dennett"'))
        self.assertEqual([{'name': u"The Mind's I"}, {'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Book" + author:"Douglas Hofstadter" * author:"Daniel Dennett"'))

    def test_complex(self):
        result = WikiPage.wikiquery(u'schema:"Thing/CreativeWork/Book/" > name, author')
        self.assertEqual([u'Daniel Dennett', u'Douglas Hofstadter'], [v.pvalue for v in result[0]['author']])
        self.assertEqual(u'The Mind\'s I', result[0]['name'].pvalue)
        self.assertEqual(u'Douglas Hofstadter', result[1]['author'].pvalue)
        self.assertEqual(u'GEB', result[1]['name'].pvalue)


class AclEvaluationTest(AppEngineTestCase):
    def setUp(self):
        super(AclEvaluationTest, self).setUp()
        self.login('a@x.com', 'ak')
        self.update_page(u'.schema Book\n.read all\nHello', u'A')
        self.update_page(u'.schema Book\n.read a@x.com\nThere', u'B')

    def test_normal(self):
        self.assertEqual({u'name': u'A'}, WikiPage.wikiquery(u'schema:"Book"'))

    def test_anonymous(self):
        self.assertEqual({u'name': u'A'}, WikiPage.wikiquery(u'schema:"Book" > name'))

    def test_user_with_no_permission(self):
        user = users.User('a@y.com')
        self.assertEqual({u'name': u'A'}, WikiPage.wikiquery(u'schema:"Book"', user))

    def test_user_with_permission(self):
        user = users.User('a@x.com')
        self.assertEqual([{u'name': u'A'}, {u'name': u'B'}], WikiPage.wikiquery(u'schema:"Book"', user))
