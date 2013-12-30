# -*- coding: utf-8 -*-
import schema
import unittest2 as unittest
from tests import AppEngineTestCase
from models import WikiPage, SchemaDataIndex


class SchemaTest(AppEngineTestCase):
    def setUp(self):
        super(SchemaTest, self).setUp()

    def test_get_plural_label(self):
        self.assertEqual(u'Creative Works', schema.get_schema('CreativeWork')['plural_label'])
        self.assertEqual(u'Medical Entities', schema.get_schema('MedicalEntity')['plural_label'])
        self.assertEqual(u'Local Businesses', schema.get_schema('LocalBusiness')['plural_label'])
        self.assertEqual(u'Attorneys', schema.get_schema('Attorney')['plural_label'])

    def test_get_custom_plural_label_for_irregular_noun(self):
        self.assertEqual(u'People', schema.get_schema('Person')['plural_label'])

    def test_get_property_label(self):
        self.assertEqual(u'Author', schema.get_property('author')['label'])
        self.assertEqual(u'Authored %s', schema.get_property('author')['reversed_label'])

    def test_get_property_label_for_custom_reversed_form(self):
        self.assertEqual(u'Date Published', schema.get_property('datePublished')['label'])
        self.assertEqual(u'Published %s', schema.get_property('datePublished')['reversed_label'])

    def test_incoming_links(self):
        self.assertEqual(u'Related People', schema.humane_property('Person', 'relatedTo', True))
        self.assertEqual(u'Children (People)', schema.humane_property('Person', 'parent', True))

    def test_datatype(self):
        self.assertEqual('Boolean', schema.get_datatype('Boolean')['label'])

    def test_custom_datatype(self):
        isbn = schema.get_datatype('ISBN')
        self.assertEqual(['DataType'], isbn['ancestors'])


class CustomSchemaTest(AppEngineTestCase):
    def setUp(self):
        super(CustomSchemaTest, self).setUp()
        schema.SCHEMA_FILE_TO_LOAD.append('schema-custom.json.sample')
        self.person = schema.get_schema('Person')
        self.politician = schema.get_schema('Politician')

    def tearDown(self):
        super(CustomSchemaTest, self).tearDown()
        schema.SCHEMA_FILE_TO_LOAD = schema.SCHEMA_FILE_TO_LOAD[:-1]

    def test_inheritance_relationship(self):
        self.assertTrue('Politician' in self.person['subtypes'])
        self.assertTrue('Person' in self.politician['supertypes'])
        self.assertTrue('Person' in self.politician['ancestors'])

    def test_humane_labels(self):
        self.assertEqual(u'Politician', schema.get_schema('Politician')['label'])
        self.assertEqual(u'Politicians', schema.humane_property('Politician', 'politicalParty', True))
        self.assertEqual(u'Political Party', schema.humane_property('Politician', 'politicalParty'))

    def test_property_inheritance(self):
        self.assertEqual(self.person['properties'], self.politician['properties'])
        self.assertEqual([u'politicalParty'], self.politician['specific_properties'])


class SchemaPathTest(unittest.TestCase):
    def test_humane_itemtype(self):
        self.assertEqual('Book', schema.humane_item('Book'))
        self.assertEqual('Creative Work', schema.humane_item('CreativeWork'))

    def test_humane_property(self):
        self.assertEqual('Published Books',
                         schema.humane_property('Book', 'datePublished', True))
        self.assertEqual('Date Published',
                         schema.humane_property('Book', 'datePublished'))

    def test_itemtype_path(self):
        self.assertEqual('Thing/',
                         schema.get_itemtype_path('Thing'))
        self.assertEqual('Thing/CreativeWork/Article/',
                         schema.get_itemtype_path('Article'))


class EmbeddedSchemaDataTest(AppEngineTestCase):
    def setUp(self):
        super(EmbeddedSchemaDataTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_no_data(self):
        page = self.update_page(u'Hello', u'Hello')
        self.assertEquals(['name', 'schema'], page.data.keys())
        self.assertEqual(u'Hello', page.data['name'].rawvalue)
        self.assertEqual(u'Thing/CreativeWork/Article/', page.data['schema'].rawvalue)

    def test_author_and_isbn(self):
        page = self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}')
        self.assertEqual(u'AK', page.data['author'].rawvalue)
        self.assertEqual(u'1234567890', page.data['isbn'].rawvalue)

    def test_multiple_authors(self):
        page = self.update_page(u'.schema Book\n[[author::AK]] and [[author::TK]]')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK'], [v.rawvalue for v in page.data['author']])


class YamlSchemaDataTest(AppEngineTestCase):
    def setUp(self):
        super(YamlSchemaDataTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_yaml(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "1234567890"\n\nHello', u'Hello')
        self.assertEqual({u'Book/author': [u'AK']}, page.outlinks)
        self.assertEquals({'name': u'Hello', 'isbn': u'1234567890', 'schema': u'Thing/CreativeWork/Book/', 'author': u'AK'},
                          dict((k, v.rawvalue) for k, v in page.data.items()))

    def test_list_value(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\nHello', u'Hello')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEquals([u'AK', u'TK'], [v.rawvalue for v in page.data['author']])

    def test_mix_with_embedded_data(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::1234567890}}\n\n[[author::JK]]', u'Hello')
        self.assertEqual({u'Book/author': [u'AK', u'JK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK', u'JK'], [v.rawvalue for v in page.data['author']])
        self.assertEqual(u'1234567890', page.data['isbn'].rawvalue)
        self.assertEqual(u'Hello', page.data['name'].rawvalue)

    def test_no_duplications(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::1234567890}}\n\n[[author::TK]]')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEquals([u'AK', u'TK'], [v.rawvalue for v in page.data['author']])

    def test_yaml_block_should_not_be_rendered(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "1234567890"\n\nHello')
        self.assertEqual(-1, page.rendered_body.find(u'#!yaml/schema'))


class SchemaIndexTest(AppEngineTestCase):
    def setUp(self):
        super(SchemaIndexTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_schema_index_create(self):
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}\n[[datePublished::2013]]', u'Hello')
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'author', SchemaDataIndex.value == u'AK').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'isbn', SchemaDataIndex.value == u'1234567890').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'datePublished', SchemaDataIndex.value == u'2013').count())

    def test_schema_index_update(self):
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}\n[[datePublished::2013]]', u'Hello')
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567899}}\n[[dateModified::2013]]', u'Hello')
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'author', SchemaDataIndex.value == u'AK').count())
        self.assertEqual(0, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'isbn', SchemaDataIndex.value == u'1234567890').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'isbn', SchemaDataIndex.value == u'1234567899').count())
        self.assertEqual(0, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'datePublished', SchemaDataIndex.value == u'2013').count())
        self.assertEqual(1, SchemaDataIndex.query(SchemaDataIndex.title == u'Hello', SchemaDataIndex.name == u'dateModified', SchemaDataIndex.value == u'2013').count())


class TypeConversionTest(AppEngineTestCase):
    def test_update_page_should_perform_validation(self):
        self.assertRaises(ValueError, self.update_page, u'.schema UnknownSchema')

    def test_unknown_itemtype(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'UnknownSchema', {})

    def test_invalid_property(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'UnknownSchema', {u'unknownProp': u'Hello'})

    def test_year_only_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979'})
        self.assertEqual(1979, data['birthDate'].year)
        self.assertFalse(data['birthDate'].bce)
        self.assertIsNone(data['birthDate'].month)
        self.assertIsNone(data['birthDate'].day)
        self.assertTrue(data['birthDate'].is_year_only())

    def test_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'300-05-15 BCE'})
        self.assertEqual(u'300-05-15 BCE', data['birthDate'].rawvalue)
        self.assertEqual(300, data['birthDate'].year)
        self.assertTrue(data['birthDate'].bce)
        self.assertEqual(5, data['birthDate'].month)
        self.assertEqual(15, data['birthDate'].day)
        self.assertFalse(data['birthDate'].is_year_only())

    def test_invalid_date(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'Person', {u'birthDate': u'Ten years ago'})
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'Person', {u'birthDate': u'1979-13-05'})
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'Person', {u'birthDate': u'1979-05-40'})

    def test_boolean(self):
        for l in [u'1', u'true', u'TRUE', u'yes', u'YES']:
            data = schema.SchemaConverter.convert(u'Article', {u'isFamilyFriendly': l})
            self.assertTrue(data['isFamilyFriendly'].value)
        for l in [u'0', u'false', u'FALSE', u'no', u'NO']:
            data = schema.SchemaConverter.convert(u'Article', {u'isFamilyFriendly': l})
            self.assertFalse(data['isFamilyFriendly'].value)

    def test_text(self):
        data = schema.SchemaConverter.convert(u'Person', {u'jobTitle': u'Visualization engineer'})
        self.assertEqual(u'Visualization engineer', data['jobTitle'].value)

    def test_integer(self):
        data = schema.SchemaConverter.convert(u'SoftwareApplication', {u'fileSize': u'12345'})
        self.assertEqual(12345, data['fileSize'].value)

    def test_invalid_integer(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'SoftwareApplication', {u'fileSize': u'1234.5'})
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'SoftwareApplication', {u'fileSize': u'Very small'})

    def test_number(self):
        data = schema.SchemaConverter.convert(u'JobPosting', {u'baseSalary': u'1234.5'})
        self.assertEqual(1234.5, data['baseSalary'].value)
        self.assertEqual(float, type(data['baseSalary'].value))

        data = schema.SchemaConverter.convert(u'JobPosting', {u'baseSalary': u'12345'})
        self.assertEqual(int, type(data['baseSalary'].value))

    def test_url(self):
        data = schema.SchemaConverter.convert(u'Code', {u'codeRepository': u'http://x.com/path/y.jsp?q=2&q2=2'})
        self.assertEqual('http://x.com/path/y.jsp?q=2&q2=2', data['codeRepository'].value)

    def test_invalid_url(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'Code', {u'codeRepository': u'See http://github.org'})

    def test_thing(self):
        data = schema.SchemaConverter.convert(u'Code', {u'programmingLanguage': u'JavaScript'})
        self.assertEqual('JavaScript', data['programmingLanguage'].value)

    def test_isbn(self):
        data = schema.SchemaConverter.convert(u'Book', {u'isbn': u'1234512345'})
        self.assertEqual('1234512345', data['isbn'].value)
        self.assertEqual(u'<a href="http://www.amazon.com/gp/product/1234512345" class="isbn" itemprop="isbn">1234512345</a>',
                         data['isbn'].render())

    def test_isbn_kr(self):
        data = schema.SchemaConverter.convert(u'Book', {u'isbn': u'8912345123'})
        self.assertEqual('8912345123', data['isbn'].value)
        self.assertEqual(u'<a href="http://www.aladin.co.kr/shop/wproduct.aspx?ISBN=9788912345123" class="isbn" itemprop="isbn">8912345123</a>',
                         data['isbn'].render())

        data = schema.SchemaConverter.convert(u'Book', {u'isbn': u'9788912345123'})
        self.assertEqual('9788912345123', data['isbn'].value)
        self.assertEqual(u'<a href="http://www.aladin.co.kr/shop/wproduct.aspx?ISBN=9788912345123" class="isbn" itemprop="isbn">9788912345123</a>',
                         data['isbn'].render())

    def test_list_value(self):
        data = schema.SchemaConverter.convert(u'Book', {u'author': [u'AK', u'CK']})
        self.assertEqual(list, type(data['author']))
        self.assertEqual(2, len(data['author']))
        self.assertEqual(u'AK', data['author'][0].value)
        self.assertEqual(u'CK', data['author'][1].value)
