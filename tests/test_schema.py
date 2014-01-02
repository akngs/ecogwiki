# -*- coding: utf-8 -*-
import schema
import unittest2 as unittest
from tests import AppEngineTestCase
from models import SchemaDataIndex, PageOperationMixin


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

    def test_legacy_spells(self):
        self.assertRaises(KeyError, schema.get_property, 'contactPoints')
        self.assertTrue('awards' not in schema.get_schema('Person')['properties'])

    def test_incoming_links(self):
        self.assertEqual(u'Related People', schema.humane_property('Person', 'relatedTo', True))
        self.assertEqual(u'Children (People)', schema.humane_property('Person', 'parent', True))

    def test_datatype(self):
        self.assertEqual('Boolean', schema.get_datatype('Boolean')['label'])

    def test_custom_datatype(self):
        isbn = schema.get_datatype('ISBN')
        self.assertEqual(['DataType'], isbn['ancestors'])


class CustomTypeAndPropertyTest(AppEngineTestCase):
    def setUp(self):
        super(CustomTypeAndPropertyTest, self).setUp()
        schema.SCHEMA_TO_LOAD.append('schema-custom.json.sample')
        self.person = schema.get_schema('Person')
        self.politician = schema.get_schema('Politician')

    def tearDown(self):
        schema.SCHEMA_TO_LOAD = schema.SCHEMA_TO_LOAD[:-1]
        super(CustomTypeAndPropertyTest, self).tearDown()

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

    def test_default_cardinality(self):
        self.assertEqual([0, 0], schema.get_cardinality('Person', 'children'))

    def test_prop_cardinality(self):
        self.assertEqual([1, 1], schema.get_cardinality('Thing', 'url'))

    def test_cardinality_in_item_should_override_prop_candinality(self):
        self.assertEqual([0, 1], schema.get_cardinality('Person', 'url'))


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


class EmbeddedSchemaDataTest(unittest.TestCase):
    def test_no_data(self):
        data = PageOperationMixin.parse_data(u'Hello', u'Hello')
        self.assertEquals(['name', 'schema'], data.keys())
        self.assertEqual(u'Hello', data['name'].pvalue)
        self.assertEqual(u'Thing/CreativeWork/Article/', data['schema'].pvalue)

    def test_author_and_isbn(self):
        data = PageOperationMixin.parse_data(u'Hello', u'[[author::AK]]\n{{isbn::1234567890}}', u'Book')
        self.assertEqual(u'AK', data['author'].pvalue)
        self.assertEqual(u'1234567890', data['isbn'].pvalue)

    def test_multiple_authors(self):
        data = PageOperationMixin.parse_data(u'Hello', u'[[author::AK]] and [[author::TK]]', u'Book')
        self.assertEqual([u'AK', u'TK'], [v.pvalue for v in data['author']])


class YamlSchemaDataTest(AppEngineTestCase):
    def setUp(self):
        super(YamlSchemaDataTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_yaml(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "1234567890"\n\nHello', u'Hello')
        self.assertEqual({u'Book/author': [u'AK']}, page.outlinks)
        self.assertEquals({'name': u'Hello', 'isbn': u'1234567890', 'schema': u'Thing/CreativeWork/Book/', 'author': u'AK'},
                          dict((k, v.pvalue) for k, v in page.data.items()))

    def test_list_value(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\nHello', u'Hello')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEquals([u'AK', u'TK'], [v.pvalue for v in page.data['author']])

    def test_mix_with_embedded_data(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::1234567890}}\n\n[[author::JK]]', u'Hello')
        self.assertEqual({u'Book/author': [u'AK', u'JK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK', u'JK'], [v.pvalue for v in page.data['author']])
        self.assertEqual(u'1234567890', page.data['isbn'].pvalue)
        self.assertEqual(u'Hello', page.data['name'].pvalue)

    def test_no_duplications(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::1234567890}}\n\n[[author::TK]]')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEquals([u'AK', u'TK'], [v.pvalue for v in page.data['author']])

    def test_yaml_block_should_not_be_rendered(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "1234567890"\n\nHello')
        self.assertEqual(-1, page.rendered_body.find(u'#!yaml/schema'))


class SchemaIndexTest(AppEngineTestCase):
    def setUp(self):
        super(SchemaIndexTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_schema_index_create(self):
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}\n[[datePublished::2013]]', u'Hello')
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'author', u'AK'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'isbn', u'1234567890'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'datePublished', u'2013'))

    def test_schema_index_update(self):
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}\n[[datePublished::2013]]', u'Hello')
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567899}}\n[[dateModified::2013]]', u'Hello')
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'author', u'AK'))
        self.assertFalse(SchemaDataIndex.has_match(u'Hello', u'isbn', u'1234567890'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'isbn', u'1234567899'))
        self.assertFalse(SchemaDataIndex.has_match(u'Hello', u'datePublished', u'2013'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'dateModified', u'2013'))

    def test_rebuild(self):
        page = self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}\n[[datePublished::2013]]', u'Hello')
        SchemaDataIndex.rebuild_index(page.title, page.data)
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'author', u'AK'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'isbn', u'1234567890'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'datePublished', u'2013'))


class TypeConversionTest(unittest.TestCase):
    def test_unknown_itemtype(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'UnknownSchema', {})

    def test_invalid_property(self):
        data = schema.SchemaConverter.convert(u'Book', {u'unknownProp': u'Hello'})['unknownProp']
        self.assertEqual(schema.InvalidProperty, type(data))

    def test_year_only_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979'})
        self.assertEqual(1979, data['birthDate'].year)
        self.assertFalse(data['birthDate'].bce)
        self.assertIsNone(data['birthDate'].month)
        self.assertIsNone(data['birthDate'].day)
        self.assertTrue(data['birthDate'].is_year_only())

    def test_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'300-05-15 BCE'})
        self.assertEqual(u'300-05-15 BCE', data['birthDate'].pvalue)
        self.assertEqual(300, data['birthDate'].year)
        self.assertTrue(data['birthDate'].bce)
        self.assertEqual(5, data['birthDate'].month)
        self.assertEqual(15, data['birthDate'].day)
        self.assertFalse(data['birthDate'].is_year_only())

    def test_partial_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979'})['birthDate']
        self.assertEqual(1979, data.year)
        self.assertTrue(data.is_year_only())

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-03-??'})['birthDate']
        self.assertEqual(1979, data.year)
        self.assertEqual(3, data.month)
        self.assertEqual(1, data.day)
        self.assertFalse(data.is_year_only())

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-??-??'})['birthDate']
        self.assertEqual(1979, data.year)
        self.assertTrue(data.is_year_only())

    def test_invalid_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'Ten years ago'})['birthDate']
        self.assertEqual(schema.InvalidProperty, type(data))
        self.assertEqual(u'Ten years ago', data.pvalue)

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-13-05'})['birthDate']
        self.assertEqual(schema.InvalidProperty, type(data))
        self.assertEqual(u'1979-13-05', data.pvalue)

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-05-40'})['birthDate']
        self.assertEqual(schema.InvalidProperty, type(data))
        self.assertEqual(u'1979-05-40', data.pvalue)

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

    def test_name_text(self):
        data = schema.SchemaConverter.convert(u'Person', {u'name': u'AK'})
        self.assertEqual(True, data['name'].is_wikilink())
        self.assertEqual(u'<a class="wikipage" href="/AK">AK</a>', data['name'].render())

    def test_integer(self):
        data = schema.SchemaConverter.convert(u'SoftwareApplication', {u'fileSize': u'12345'})
        self.assertEqual(12345, data['fileSize'].value)

    def test_invalid_integer(self):
        data = schema.SchemaConverter.convert(u'SoftwareApplication', {u'fileSize': u'1234.5'})['fileSize']
        self.assertEqual(schema.InvalidProperty, type(data))
        data = schema.SchemaConverter.convert(u'SoftwareApplication', {u'fileSize': u'Very small'})['fileSize']
        self.assertEqual(schema.InvalidProperty, type(data))

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
        data = schema.SchemaConverter.convert(u'Code', {u'codeRepository': u'See http://github.org'})['codeRepository']
        self.assertEqual(schema.InvalidProperty, type(data))

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


class TypeConversionWithCardinalityTest(AppEngineTestCase):
    def setUp(self):
        super(TypeConversionWithCardinalityTest, self).setUp()
        schema.SCHEMA_TO_LOAD.append('schema-custom.json.sample')

    def tearDown(self):
        schema.SCHEMA_TO_LOAD = schema.SCHEMA_TO_LOAD[:-1]
        super(TypeConversionWithCardinalityTest, self).tearDown()

    def test_props_gt_cardinality(self):
        data = schema.SchemaConverter.convert(u'Person', {'url': ['http://x.com', 'http://y.com']})
        self.assertEqual('http://x.com', data['url'].value)

    def test_props_lt_cardinality(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'Thing', {})


class ConversionPriorityTest(unittest.TestCase):
    def test_try_url_first_then_text(self):
        prop = schema.SchemaConverter.convert(u'SoftwareApplication', {u'featureList': u'http://x.com'})['featureList']
        self.assertEqual(schema.URLProperty, type(prop))

        prop = schema.SchemaConverter.convert(u'SoftwareApplication', {u'featureList': u'See http://x.com'})['featureList']
        self.assertEqual(schema.TextProperty, type(prop))
