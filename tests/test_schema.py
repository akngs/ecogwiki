# -*- coding: utf-8 -*-
import schema
import caching
import unittest2 as unittest
from tests import AppEngineTestCase
from models import SchemaDataIndex, PageOperationMixin, WikiPage


class LabelTest(AppEngineTestCase):
    def setUp(self):
        super(LabelTest, self).setUp()

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


class CustomTypeAndPropertyTest(AppEngineTestCase):
    def setUp(self):
        super(CustomTypeAndPropertyTest, self).setUp()
        schema.SCHEMA_TO_LOAD.append({
            "datatypes": {
            },
            "properties": {
                "politicalParty": {
                    "comment": "Political party.",
                    "comment_plain": "Political party.",
                    "domains": [
                        "Thing"
                    ],
                    "id": "politicalParty",
                    "label": "Political Party",
                    "reversed_label": "%s",
                    "ranges": [
                        "Text"
                    ]
                }
            },
            "types": {
                "Politician": {
                    "ancestors": [
                        "Thing",
                        "Person"
                    ],
                    "comment": "",
                    "comment_plain": "",
                    "id": "Politician",
                    "label": "Politician",
                    "specific_properties": [
                        "politicalParty"
                    ],
                    "subtypes": [],
                    "supertypes": [
                        "Person"
                    ],
                    "url": "http://www.ecogwiki.com/sp.schema/types/Politician"
                }
            }
        })
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
        person = set(schema.get_schema('Person')['properties'])
        politician = set(schema.get_schema('Politician')['properties'])
        self.assertEqual(set(), person.difference(politician))
        self.assertEqual({u'politicalParty'}, politician.difference(person))


class SimpleCustomTypeAndPropertyTest(AppEngineTestCase):
    def setUp(self):
        super(SimpleCustomTypeAndPropertyTest, self).setUp()
        schema.SCHEMA_TO_LOAD.append({
            "datatypes": {
                "ISBN2": {
                    "comment": "ISBN 2",
                },
            },
            "properties": {
                "politicalParty": {
                    "comment": "A political party.",
                }
            },
            "types": {
                "Politician": {
                    "supertypes": ["Person"],
                    "specific_properties": ["politicalParty"],
                    "comment": "A political party.",
                }
            }
        })
        self.dtype = schema.get_datatype('ISBN2')
        self.item = schema.get_schema('Politician')
        self.prop = schema.get_property('politicalParty')

    def tearDown(self):
        schema.SCHEMA_TO_LOAD = schema.SCHEMA_TO_LOAD[:-1]
        super(SimpleCustomTypeAndPropertyTest, self).tearDown()

    def test_populate_omitted_item_fields(self):
        self.assertEqual('/sp.schema/types/Politician', self.item['url'])
        self.assertEqual(["Thing", "Person"], self.item['ancestors'])
        self.assertEqual('Politician', self.item['id'])
        self.assertEqual('A political party.', self.item['comment_plain'])
        self.assertEqual([], self.item['subtypes'])

    def test_populate_omitted_datatype_fields(self):
        self.assertEqual('/sp.schema/datatypes/ISBN2', self.dtype['url'])
        self.assertEqual(["Thing", "Person"], self.item['ancestors'])
        self.assertEqual([], self.dtype['properties'])
        self.assertEqual([], self.dtype['specific_properties'])
        self.assertEqual(['DataType'], self.dtype['ancestors'])
        self.assertEqual(['DataType'], self.dtype['supertypes'])
        self.assertEqual([], self.dtype['subtypes'])
        self.assertEqual('ISBN2', self.dtype['id'])
        self.assertEqual('ISBN 2', self.dtype['comment_plain'])

    def test_populate_omitted_property_fields(self):
        self.assertEqual(["Thing"], self.prop['domains'])
        self.assertEqual(["Text"], self.prop['ranges'])
        self.assertEqual('A political party.', self.item['comment_plain'])


class EnumerationTest(AppEngineTestCase):
    def setUp(self):
        super(EnumerationTest, self).setUp()
        schema.SCHEMA_TO_LOAD.append({
            "types": {
                "Student": {
                    "ancestors": ["Thing", "Person"],
                    "id": "Student",
                    "label": "Student",
                    "specific_properties": ["academicSeason"],
                    "subtypes": [],
                    "supertypes": ["Person"],
                    "url": "http://www.ecogwiki.com/sp.schema/types/Student",
                }
            },
            "properties": {
                "academicSeason": {
                    "label": "Academic Season",
                    "domains": ["Student"],
                    "ranges": ["Text"],
                    "enum": ["1-1", "1-2", "2-1", "2-2"]
                }
            },
        })

    def tearDown(self):
        schema.SCHEMA_TO_LOAD = schema.SCHEMA_TO_LOAD[:-1]
        super(EnumerationTest, self).tearDown()

    def test_enum(self):
        data = schema.SchemaConverter.convert(u'Student', {u'academicSeason': u'1-1'})['academicSeason']
        self.assertEqual(schema.TextProperty, type(data))
        self.assertEqual(u'1-1', data.render())

        data = schema.SchemaConverter.convert(u'Student', {u'academicSeason': u'1-3'})['academicSeason']
        self.assertEqual(schema.InvalidProperty, type(data))


class CustomCardinalityTest(AppEngineTestCase):
    def setUp(self):
        super(CustomCardinalityTest, self).setUp()
        schema.SCHEMA_TO_LOAD.append({
            "properties": {
                "url": {
                    "cardinality": [1, 1]
                }
            },
            "types": {
                "Person": {
                    "cardinalities": {
                        "url": [0, 1]
                    }
                }
            }
        })

    def tearDown(self):
        schema.SCHEMA_TO_LOAD = schema.SCHEMA_TO_LOAD[:-1]
        super(CustomCardinalityTest, self).tearDown()

    def test_props_gt_cardinality(self):
        data = schema.SchemaConverter.convert(u'Person', {'url': ['http://x.com', 'http://y.com']})
        self.assertEqual('http://x.com', data['url'].value)

    def test_props_lt_cardinality(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'Thing', {})

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


class SectionTest(unittest.TestCase):
    def test_default_section(self):
        data = PageOperationMixin.parse_sections(u'Hello')
        self.assertEqual({'articleBody'}, set(data.keys()))
        self.assertEqual(u'Hello', data['articleBody'])

    def test_specifying_default_section(self):
        data = PageOperationMixin.parse_sections(u'Hello', u'longText')
        self.assertEqual({'longText'}, set(data.keys()))
        self.assertEqual(u'Hello', data['longText'])

    def test_additional_sections(self):
        data = PageOperationMixin.parse_sections(u'Hello\n\nsection1::---\n\nHello\n\nthere\n\nsection2::---\n\nGood\n\nbye\n')
        self.assertEqual({'articleBody', 'section1', 'section2'}, set(data.keys()))
        self.assertEqual(u'Hello', data['articleBody'])
        self.assertEqual(u'Hello\n\nthere', data['section1'])
        self.assertEqual(u'Good\n\nbye', data['section2'])


class EmbeddedSchemaDataTest(unittest.TestCase):
    def test_no_data(self):
        data = PageOperationMixin.parse_data(u'Hello', u'Hello')
        self.assertEqual(['articleBody', 'name', 'schema'], data.keys())
        self.assertEqual(u'Hello', data['name'].pvalue)
        self.assertEqual(u'Thing/CreativeWork/Article/', data['schema'].pvalue)
        self.assertEqual(u'Hello', data['articleBody'].pvalue)

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

        data_items = dict((k, v.pvalue) for k, v in page.data.items())
        del data_items['datePageModified']

        self.assertEqual(
            {'name': u'Hello', 'isbn': u'1234567890', 'schema': u'Thing/CreativeWork/Book/', 'author': u'AK', 'longDescription': u'Hello'},
            data_items
        )

    def test_re_match(self):
        body = u'''\t#!yaml/schema\n    url: "http://anotherfam.kr/"\n\n\n[[\uc81c\uc791\ub450\ub808]]\ub97c ...\n'''
        data = PageOperationMixin.parse_schema_yaml(body)
        self.assertEqual(data['url'], 'http://anotherfam.kr/')

    def test_list_value(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\nHello', u'Hello')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK'], [v.pvalue for v in page.data['author']])

    def test_mix_with_embedded_data(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::1234567890}}\n\n[[author::JK]]', u'Hello')
        self.assertEqual({u'Book/author': [u'AK', u'JK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK', u'JK'], [v.pvalue for v in page.data['author']])
        self.assertEqual(u'1234567890', page.data['isbn'].pvalue)
        self.assertEqual(u'Hello', page.data['name'].pvalue)

    def test_no_duplications(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n\n{{isbn::1234567890}}\n\n[[author::TK]]')
        self.assertEqual({u'Book/author': [u'AK', u'TK']}, page.outlinks)
        self.assertEqual([u'AK', u'TK'], [v.pvalue for v in page.data['author']])

    def test_yaml_block_should_not_be_rendered(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: AK\n    isbn: "1234567890"\n\nHello')
        self.assertEqual(-1, page.rendered_body.find(u'#!yaml/schema'))

    def test_tab_and_space_mixed(self):
        body = u'\t#!yaml/schema\n    alternateName: hi\n\turl: http://x.com\n    name: "Hello"\n'
        data = PageOperationMixin.parse_schema_yaml(body)
        self.assertEqual(data['name'], u'Hello')
        self.assertEqual(data['alternateName'], u'hi')
        self.assertEqual(data['url'], u'http://x.com')

    def test_yaml_indent_catching_only_space(self):
        body = u'''\n\t#!yaml/schema\n    url: "http://x.com"\n\nHello\n'''
        matched = PageOperationMixin.re_yaml_schema.search(body).group(0)
        self.assertTrue(matched.startswith('\t'))

    def test_rawdata(self):
        page = self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: [AK, TK]\n', u'Hello')
        raw = page.rawdata
        self.assertEqual(u'Hello', raw['name'])
        self.assertEqual([u'AK', u'TK'], raw['author'])


class SchemaIndexTest(AppEngineTestCase):
    def setUp(self):
        super(SchemaIndexTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_create(self):
        self.update_page(u'.schema Book\n[[author::AK]]\n{{isbn::1234567890}}\n[[datePublished::2013]]', u'Hello')
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'author', u'AK'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'isbn', u'1234567890'))
        self.assertTrue(SchemaDataIndex.has_match(u'Hello', u'datePublished', u'2013'))

    def test_update(self):
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

    def test_should_not_index_for_longtext(self):
        self.update_page(u'longDescription::---\n\nHello there', u'Hello')
        self.assertFalse(SchemaDataIndex.has_match(u'Hello', u'longDescription', u'Hello there'))


class TypeConversionTest(unittest.TestCase):
    def test_unknown_itemtype(self):
        self.assertRaises(ValueError, schema.SchemaConverter.convert, u'UnknownSchema', {})

    def test_invalid_property(self):
        data = schema.SchemaConverter.convert(u'Book', {u'unknownProp': u'Hello'})['unknownProp']
        self.assertEqual(schema.InvalidProperty, type(data))

    def test_year_only_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979 BCE'})
        self.assertEqual(1979, data['birthDate'].year)
        self.assertTrue(data['birthDate'].bce)
        self.assertIsNone(data['birthDate'].month)
        self.assertIsNone(data['birthDate'].day)
        self.assertTrue(data['birthDate'].is_year_only())
        self.assertEqual(u'<time datetime="1979 BCE"><a class="wikipage" href="/1979_BCE">1979</a><span> BCE</span></time>', data['birthDate'].render())

    def test_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'300-05-15 BCE'})
        self.assertEqual(u'300-05-15 BCE', data['birthDate'].pvalue)
        self.assertEqual(300, data['birthDate'].year)
        self.assertTrue(data['birthDate'].bce)
        self.assertEqual(5, data['birthDate'].month)
        self.assertEqual(15, data['birthDate'].day)
        self.assertFalse(data['birthDate'].is_year_only())
        self.assertEqual(u'<time datetime="300-05-15 BCE"><a class="wikipage" href="/300_BCE">300</a><span>-</span><a class="wikipage" href="/May_15">05-15</a><span> BCE</span></time>', data['birthDate'].render())

    def test_partial_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979'})['birthDate']
        self.assertEqual(1979, data.year)
        self.assertTrue(data.is_year_only())
        self.assertEqual(u'<time datetime="1979"><a class="wikipage" href="/1979">1979</a></time>', data.render())

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-03-??'})['birthDate']
        self.assertEqual(1979, data.year)
        self.assertEqual(3, data.month)
        self.assertEqual(1, data.day)
        self.assertFalse(data.is_year_only())
        self.assertEqual(u'<time datetime="1979-03-??"><a class="wikipage" href="/1979">1979</a><span>-</span><a class="wikipage" href="/March">03-??</a></time>', data.render())

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-??-??'})['birthDate']
        self.assertEqual(1979, data.year)
        self.assertEqual(u'<time datetime="1979-??-??"><a class="wikipage" href="/1979">1979</a><span>-</span><span>??-??</span></time>', data.render())

    def test_invalid_date(self):
        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'Ten years ago'})['birthDate']
        self.assertEqual(schema.InvalidProperty, type(data))
        self.assertEqual(u'Ten years ago', data.pvalue)
        self.assertEqual(u'<span class="error">Ten years ago</span>', data.render())

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-13-05'})['birthDate']
        self.assertEqual(schema.InvalidProperty, type(data))
        self.assertEqual(u'1979-13-05', data.pvalue)
        self.assertEqual(u'<span class="error">1979-13-05</span>', data.render())

        data = schema.SchemaConverter.convert(u'Person', {u'birthDate': u'1979-05-40'})['birthDate']
        self.assertEqual(schema.InvalidProperty, type(data))
        self.assertEqual(u'1979-05-40', data.pvalue)
        self.assertEqual(u'<span class="error">1979-05-40</span>', data.render())

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

    def test_embeddable_url(self):
        data = schema.SchemaConverter.convert(u'Thing', {u'image': u'http://x.com/a.png'})
        self.assertEqual(u'http://x.com/a.png', data['image'].value)
        self.assertEqual(schema.EmbeddableURLProperty, type(data['image']))

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


class ConversionPriorityTest(unittest.TestCase):
    def test_try_url_first_then_text(self):
        prop = schema.SchemaConverter.convert(u'SoftwareApplication', {u'featureList': u'http://x.com'})['featureList']
        self.assertEqual(schema.URLProperty, type(prop))

        prop = schema.SchemaConverter.convert(u'SoftwareApplication', {u'featureList': u'See http://x.com'})['featureList']
        self.assertEqual(schema.TextProperty, type(prop))


class SchemaChangeTest(AppEngineTestCase):
    def setUp(self):
        super(SchemaChangeTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def tearDown(self):
        schema.SCHEMA_TO_LOAD = schema.SCHEMA_TO_LOAD[:-1]
        super(SchemaChangeTest, self).tearDown()

    def test_change_schema_after_writing_and_try_to_read(self):
        self.update_page(u'Hello there?', u'Hello')

        caching.flush_all()
        schema.SCHEMA_TO_LOAD.append({
            "properties": {
                "author": {
                    "cardinality": [1, 1]
                }
            }
        })

        page = WikiPage.get_by_title(u'Hello')
        page.rendered_body

    def test_change_schema_after_writing_and_try_to_update(self):
        self.update_page(u'Hello there?', u'Hello')

        caching.flush_all()
        schema.SCHEMA_TO_LOAD.append({
            "properties": {
                "author": {
                    "cardinality": [1, 1]
                }
            }
        })

        self.update_page(u'.schema Book\n\n    #!yaml/schema\n    author: "Alan Kang"\n\nHello there?\n', u'Hello')


class MiscTest(AppEngineTestCase):
    def setUp(self):
        super(MiscTest, self).setUp()

    def test_should_not_allow_legacy_spells(self):
        self.assertRaises(KeyError, schema.get_property, 'contactPoints')
        self.assertTrue('awards' not in schema.get_schema('Person')['properties'])

    def test_get_datatype(self):
        self.assertEqual('Boolean', schema.get_datatype('Boolean')['label'])

    def test_get_custom_datatype(self):
        isbn = schema.get_datatype('ISBN')
        self.assertEqual(['DataType'], isbn['ancestors'])

    def test_get_itemtypes(self):
        itemtypes = schema.get_itemtypes()
        self.assertEqual(list, type(itemtypes))
        self.assertEqual(('APIReference', 'API Reference'), itemtypes[0])
        self.assertEqual(('Zoo', 'Zoo'), itemtypes[-1])

    def test_properties_should_contain_all_specific_properties(self):
        for t, _ in schema.get_itemtypes():
            item = schema.get_schema(t)
            self.assertEqual(set(), set(item['specific_properties']).difference(item['properties']))

    def test_properties_order_should_follow_that_of_source(self):
        article = schema.get_schema('Article')
        self.assertEqual('additionalType', article['properties'][0])
        self.assertEqual('longDescription', article['properties'][-1])

    def test_self_contained_schema(self):
        s = schema.get_schema('Person', True)
        url = s['properties']['url']
        self.assertEqual(dict, type(url))
        self.assertEqual([0, 0], url['cardinality'])
        self.assertEqual(['URL'], url['type']['ranges'])
