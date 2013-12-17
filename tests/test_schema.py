# -*- coding: utf-8 -*-
import cache
import schema
import unittest2 as unittest
from google.appengine.ext import testbed
from models import WikiPage, SchemaDataIndex


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

    def test_get_schema_label(self):
        self.assertEqual(u'Creative Work', schema.get_schema('CreativeWork')['label'])
        self.assertEqual(u'Creative Works', schema.get_schema('CreativeWork')['plural_label'])

    def test_get_schema_label_for_custom_plural_form(self):
        self.assertEqual(u'Person', schema.get_schema('Person')['label'])
        self.assertEqual(u'People', schema.get_schema('Person')['plural_label'])

    def test_get_property_label(self):
        self.assertEqual(u'Author', schema.get_property('author')['label'])
        self.assertEqual(u'Authored %s', schema.get_property('author')['reversed_label'])

    def test_get_property_label_for_custom_reversed_form(self):
        self.assertEqual(u'Date Published', schema.get_property('datePublished')['label'])
        self.assertEqual(u'Published %s', schema.get_property('datePublished')['reversed_label'])

    def test_incoming_links(self):
        self.assertEqual(u'Related People', schema.humane_property('Person', 'relatedTo', True))


# TODO: Delete it after finishing migration
class SchemaPathTest(unittest.TestCase):
    def test_humane_itemtype(self):
        self.assertEqual('Book', schema.humane_item('Book'))
        self.assertEqual('Creative Work', schema.humane_item('CreativeWork'))

    def test_humane_property(self):
        self.assertEqual('Published Books',
                         schema.humane_property('Book', 'datePublished', True))
        self.assertEqual('Date Published',
                         schema.humane_property('Book', 'datePublished', False))

    def test_itemtype_path(self):
        self.assertEqual('Thing/',
                         schema.get_itemtype_path('Thing'))
        self.assertEqual('Thing/CreativeWork/Article/',
                         schema.get_itemtype_path('Article'))


class EmbeddedSchemaDataTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        cache.prc.flush_all()

    def tearDown(self):
        self.testbed.deactivate()

    def test_no_data(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0)
        self.assertEquals({'name': u'Hello', 'schema': u'Thing/CreativeWork/Article/'}, page.data)

    def test_author_and_isbn(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n[[author::AK]]\n{{isbn::123456789}}', 0)
        self.assertEqual(u'AK', page.data['author'])
        self.assertEqual(u'123456789', page.data['isbn'])

    def test_multiple_authors(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n[[author::AK]] and [[author::TK]]', 0, dont_defer=True)
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK'], page.data['author'])

    def test_normal_links(self):
        page_a = WikiPage.get_by_title(u'A')
        page_a.update_content(u'[[B]]', 0, dont_defer=True)
        page_b = WikiPage.get_by_title(u'B')

        self.assertEqual([u'A'], page_b.data['inlinks'])
        self.assertEqual([u'B'], page_a.data['outlinks'])


class YamlSchemaDataTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        cache.prc.flush_all()

    def tearDown(self):
        self.testbed.deactivate()

    def test_yaml(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "123456789"\n\nHello', 0, dont_defer=True)
        self.assertEqual({u'Book/author': [u'AK']}, page.outlinks)
        self.assertEquals({'name': u'Hello', 'isbn': u'123456789', 'schema': u'Thing/CreativeWork/Book/', 'author': u'AK'}, page.data)

    def test_list_value(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\nHello', 0, dont_defer=True)
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEquals([u'AK', u'TK'], page.data['author'])

    def test_mix_with_embedded_data(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::123456789}}\n\n[[author::JK]]', 0, dont_defer=True)
        self.assertEqual({u'Book/author': [u'AK', u'JK', u'TK']}, page.outlinks)
        self.assertEquals({'name': u'Hello', 'isbn': u'123456789', 'schema': u'Thing/CreativeWork/Book/', 'author': [u'AK', u'TK', u'JK']}, page.data)

    def test_yaml_block_should_not_be_rendered(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "123456789"\n\nHello', 0)
        self.assertEqual(-1, page.rendered_body.find(u'#!yaml/schema'))


class SchemaIndexTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        cache.prc.flush_all()

    def tearDown(self):
        self.testbed.deactivate()

    def test_schema_index_create(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n[[author::AK]]\n{{isbn::123456789}}\n[[datePublished::2013]]', 0)
        page.rebuild_data_index()
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'author', SchemaDataIndex.value == u'AK').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'isbn', SchemaDataIndex.value == u'123456789').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'datePublished', SchemaDataIndex.value == u'2013').count())

    def test_schema_index_update(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n[[author::AK]]\n{{isbn::123456789}}\n[[datePublished::2013]]', 0)
        page.update_content(u'.schema Book\n[[author::AK]]\n{{isbn::123456780}}\n[[dateModified::2013]]', 1)
        page.rebuild_data_index()
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'author', SchemaDataIndex.value == u'AK').count())
        self.assertEqual(0, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'isbn', SchemaDataIndex.value == u'123456789').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'isbn', SchemaDataIndex.value == u'123456780').count())
        self.assertEqual(0, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'datePublished', SchemaDataIndex.value == u'2013').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'dateModified', SchemaDataIndex.value == u'2013').count())
