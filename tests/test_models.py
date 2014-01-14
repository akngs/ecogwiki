# -*- coding: utf-8 -*-
import main
import unittest2 as unittest
from itertools import groupby
from tests import AppEngineTestCase
from google.appengine.api import users
from markdownext.md_wikilink import parse_wikilinks
from models import WikiPage, PageOperationMixin, UserPreferences, title_grouper, ConflictError


class PartialUpdateTest(AppEngineTestCase):
    def setUp(self):
        super(PartialUpdateTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_checkbox(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'[ ] Item A\n[x] Item B', 0, user=self.get_cur_user())
        page.update_content(u'1', 1, partial='checkbox[0]', user=self.get_cur_user())

        self.assertEqual(u'[x] Item A\n[x] Item B', page.body)
        self.assertEqual(2, page.revision)
        
        page.update_content(u'0', 1, partial='checkbox[1]', user=self.get_cur_user())
        self.assertEqual(u'[x] Item A\n[ ] Item B', page.body)
        self.assertEqual(3, page.revision)

    def test_should_preserve_metadata_after_update(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub\n[ ] Item A', 0, user=self.get_cur_user())
        page.update_content(u'1', 1, partial='checkbox[0]', user=self.get_cur_user())
        self.assertEqual(2, page.revision)
        self.assertEqual(u'.pub\n[x] Item A', page.body)


class PageUpdateTest(AppEngineTestCase):
    def test_should_update_acls(self):
        self.login('ak', 'ak', True)
        page = self.update_page(u'.read test1\n.write test2, test3\nHello')
        self.assertEqual(u'test1', page.acl_read)
        self.assertEqual(u'test2, test3', page.acl_write)

        page = self.update_page(u'Hello')
        self.assertEqual(u'', page.acl_read)
        self.assertEqual(u'', page.acl_write)

    def test_should_create_revision(self):
        self.login('ak', 'ak')
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0, user=self.get_cur_user())
        page.update_content(u'Hello 2', 1, user=self.get_cur_user())

        revs = list(page.revisions)
        self.assertEqual(2, len(revs))
        self.assertEqual(u'Hello', revs[0].body)
        self.assertEqual(u'Hello 2', revs[1].body)

    def test_should_not_create_revision_if_content_is_not_changed(self):
        self.login('ak', 'ak')
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0, user=self.get_cur_user())
        page.update_content(u'Hello', 1, user=self.get_cur_user())

        revs = list(page.revisions)
        self.assertEqual(1, len(revs))
        self.assertEqual(u'Hello', revs[0].body)

    def test_automerge(self):
        self.login('ak', 'ak')
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'A\nB\nC', 0, user=self.get_cur_user())

        # remove B
        page.update_content(u'A\nC', 1, user=self.get_cur_user())
        # append D
        page.update_content(u'A\nB\nC\nD', 1, user=self.get_cur_user())

        # should be merged
        page = WikiPage.get_by_title(u'Hello')
        self.assertEqual(u'A\nC\nD', page.body)
        self.assertEqual(3, page.revision)

        revs = list(page.revisions)
        self.assertEqual(3, len(revs))

    def test_conflict(self):
        self.login('ak', 'ak')
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'A\nB\nC', 0, user=self.get_cur_user())

        # update second line
        page.update_content(u'A\nD\nC', 1, user=self.get_cur_user())

        # update second line concurrently
        self.assertRaises(ConflictError, page.update_content, u'A\nE\nC', 1, user=self.get_cur_user())

        # page should not be updated
        page = WikiPage.get_by_title(u'Hello')
        self.assertEqual(u'A\nD\nC', page.body)
        self.assertEqual(2, page.revision)

        revs = list(page.revisions)
        self.assertEqual(2, len(revs))


class PageValidationTest(AppEngineTestCase):
    def setUp(self):
        super(PageValidationTest, self).setUp()
        self.login('ak', 'ak')

    def test_schema(self):
        self.assertRaises(ValueError, self.update_page, u'.schema UnknownSchema')

    def test_duplicated_headings(self):
        self.assertRaises(ValueError, self.update_page, u'# A\n# A')

    def test_malformed_yaml_schema(self):
        self.assertRaises(ValueError, self.update_page, u'.schema Book\n\n    #!yaml/schema\n    y: [1, 2\n')

    def test_should_not_allow_self_revoking(self):
        self.update_page(u'Hello')
        self.assertRaises(ValueError, self.update_page, u'.read admin@x.com\nHello')

    def test_should_not_allow_body_if_there_is_redirect_metadata(self):
        self.assertRaises(ValueError, self.update_page, u'.redirect A\nHello')

    def test_pub_and_redirect_metatada_should_not_be_used_together(self):
        self.assertRaises(ValueError, self.update_page, u'.redirect A\n.pub')


class YamlSchemaParserTest(unittest.TestCase):
    def test_no_schema(self):
        self.assertEqual({}, PageOperationMixin.parse_schema_yaml(u'Hello'))

    def test_invalid(self):
        self.assertRaises(ValueError, PageOperationMixin.parse_schema_yaml, u'    #!yaml/schema\n    y\n')
        self.assertRaises(ValueError, PageOperationMixin.parse_schema_yaml, u'.schema Book\n\n    #!yaml/schema\n    y: [1, 2\n')


class MetadataParserTest(unittest.TestCase):
    def setUp(self):
        self.default_md = {
            'content-type': 'text/x-markdown',
            'schema': 'Article',
        }

    def test_normal(self):
        expected = {
            u'hello': u'a b c',
            u'x': None,
            u'z': u'what?',
        }
        expected.update(self.default_md)
        actual = PageOperationMixin.parse_metadata(u'.hello a b c\n.x\n.z what?\nblahblah')
        self.assertEqual(expected, actual)

    def test_empty_string(self):
        expected = {}
        expected.update(self.default_md)
        actual = PageOperationMixin.parse_metadata(u'')
        self.assertEqual(expected, actual)

    def test_no_metadata(self):
        expected = {}
        expected.update(self.default_md)
        actual = PageOperationMixin.parse_metadata(u'Hello\nThere')
        self.assertEqual(expected, actual)

    def test_get_body_only(self):
        expected = u'blahblah'
        actual = WikiPage.remove_metadata(u'.hello a b c\n.x what?\nblahblah')
        self.assertEqual(expected, actual)

    def test_line_starts_with_a_dot(self):
        expected = u'Hello\n.There'
        actual = WikiPage.remove_metadata(u'Hello\n.There')
        self.assertEqual(expected, actual)


class WikiLinkParserTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual({u'Article/relatedTo': [u'A']},
                         parse_wikilinks('Article', u'[[A]]'))

    def test_yyyy(self):
        self.assertEqual({u'Article/relatedTo': [u'1979']},
                         parse_wikilinks('Article', u'[[1979]]'))
        self.assertEqual({u'Article/relatedTo': [u'1979 BCE']},
                         parse_wikilinks('Article', u'[[1979 BCE]]'))

    def test_yyyymmdd(self):
        self.assertEqual({u'Article/relatedTo': [u'1979', u'March 27']},
                         parse_wikilinks('Article', u'[[1979-03-27]]'))
        self.assertEqual({u'Article/relatedTo': [u'1979', u'March']},
                         parse_wikilinks('Article', u'[[1979-03-??]]'))
        self.assertEqual({u'Article/relatedTo': [u'1979']},
                         parse_wikilinks('Article', u'[[1979-??-??]]'))
        self.assertEqual({u'Article/relatedTo': [u'1979 BCE', u'March 27']},
                         parse_wikilinks('Article', u'[[1979-03-27 BCE]]'))

    def test_invalid_month_or_date(self):
        self.assertEqual({u'Article/relatedTo': [u'1979-13-27']},
                         parse_wikilinks('Article', u'[[1979-13-27]]'))
        self.assertEqual({u'Article/relatedTo': [u'1979-12-50']},
                         parse_wikilinks('Article', u'[[1979-12-50]]'))
        self.assertEqual({u'Article/relatedTo': [u'1979-12-50 BCE']},
                         parse_wikilinks('Article', u'[[1979-12-50 BCE]]'))

    def test_rel(self):
        self.assertEqual({u'Article/birthDate': [u'1979 BCE', u'March 27']},
                         parse_wikilinks('Article', u'[[birthDate::1979-03-27 BCE]]'))
        self.assertEqual({u'Article/relatedTo': [u'A'], u'Article/author': [u'B']},
                         parse_wikilinks('Article', u'[[A]] [[author::B]]'))

    def test_wikiquery(self):
        self.assertEqual({}, parse_wikilinks('Article', u'[[="Hello"]]'))
        self.assertEqual({}, parse_wikilinks('Article', u'[[=schema:"Article"]]'))


class TitleToPathConvertTest(unittest.TestCase):
    def test_title_to_path(self):
        self.assertEqual('Hello_World', WikiPage.title_to_path(u'Hello World'))
        self.assertEqual('A%26B', WikiPage.title_to_path(u'A&B'))
        self.assertEqual('%EA%B0%80', WikiPage.title_to_path(u'가'))

    def test_path_to_title(self):
        self.assertEqual(u'Hello World', WikiPage.path_to_title('Hello_World'))
        self.assertEqual(u'A&B', WikiPage.path_to_title('A%26B'))
        self.assertEqual(u'가', WikiPage.path_to_title('%EA%B0%80'))


class YamlParserTest(AppEngineTestCase):
    def test_empty_page(self):
        self.assertEqual(main.DEFAULT_CONFIG, WikiPage.get_config())


class GetConfigTest(AppEngineTestCase):
    def setUp(self):
        super(GetConfigTest, self).setUp()
        self.login('ak@gmail.com', 'ak')
        self.config_page = WikiPage.get_by_title('.config')
        self.config_page.update_content(u'''
          admin:
            email: janghwan@gmail.com
          service:
            default_permissions:
              read: [all]
              write: [login]
        ''', 0, user=self.get_cur_user())

    def test_empty_config_page(self):
        config_page = WikiPage.get_by_title('.config')
        config_page.update_content('', 1, user=self.get_cur_user())

        config = WikiPage.get_config()
        perm = config['service']['default_permissions']
        self.assertEqual(perm['read'], ['all'])
        self.assertEqual(perm['write'], ['login'])

    def test_update_by_dot_config_page(self):
        config = WikiPage.get_config()
        self.assertEqual('janghwan@gmail.com', config['admin']['email'])

    def test_updates_partial_configurations(self):
        config = WikiPage.get_config()
        self.assertEqual('', config['service']['title'])


class RelatedPageUpdatingTest(AppEngineTestCase):
    def setUp(self):
        super(RelatedPageUpdatingTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_update_related_links(self):
        page = self.update_page(u'[[B]]', u'A')
        self.update_page(u'[[C]]', u'B')
        self.update_page(u'[[D]]', u'C')
        page.update_related_links()
        page.put()

        self.assertEqual({u'C': 0.025, u'D': 0.0125}, page.related_links)

    def test_redirect(self):
        page = self.update_page(u'[[B]]', u'A')
        self.update_page(u'.redirect C', u'B')
        self.update_page(u'[[D]]', u'C')
        page.update_related_links()

        self.assertTrue(u'D' in page.related_links)

    def test_prevent_self_redirect(self):
        self.assertRaises(ValueError, self.update_page, u'.redirect A', u'A')


class SimilarTitlesTest(unittest.TestCase):
    def test_similar_pages(self):
        titles = [
            u'hello',
            u'Low',
            u'hallow',
            u'what the hell',
        ]
        actual = WikiPage.similar_titles(titles, u'lo')
        expected = {
            u'startswiths': [u'Low'],
            u'endswiths': [u'hello'],
            u'contains': [u'hallow'],
        }
        self.assertEqual(expected, actual)

    def test_ignoring_special_characters(self):
        titles = [
            u'hello?',
            u'hello!',
            u'he,llo',
            u'(hello)',
        ]
        for t in titles:
            self.assertEqual(u'hello', WikiPage.normalize_title(t))

    def test_ignoring_articles(self):
        titles = [
            u'the hello there',
            u'a hello there',
            u'hello the there',
            u'hello a there',
            u'hello there the',
            u'hello there a',
        ]
        for t in titles:
            self.assertEqual(u'hellothere', WikiPage.normalize_title(t))


class DescriptionTest(unittest.TestCase):
    def test_try_newline(self):
        self.assertEqual(u'Hello', PageOperationMixin.make_description(u'Hello\nWorld', 20))

    def test_try_period(self):
        self.assertEqual(u'Hi. Hello. World.',
                         PageOperationMixin.make_description(u'Hi. Hello. World. Sentences.', 20))

    def test_cut_off(self):
        self.assertEqual(u'Hi Hello World Se...',
                         PageOperationMixin.make_description(u'Hi Hello World Sentences.', 20))

    def test_should_ignore_metadata(self):
        self.assertEqual(u'Hello',
                         PageOperationMixin.make_description(u'.pub\n\nHello', 20))

    def test_should_ignore_yaml_schema_block(self):
        self.assertEqual(u'Hello',
                         PageOperationMixin.make_description(u'.schema Book\n    #!yaml/schema\n    author: A\n\nHello', 20))


class SpecialTitlesTest(AppEngineTestCase):
    def test_years(self):
        titles = [
            u'10000 BCE',
            u'10000',
            u'1',
            u'1984',
            u'600 BCE',
        ]
        for t in titles:
            page = WikiPage.get_by_title(t)
            ss = page.special_sections
            self.assertTrue(u'years' in ss)

        normal_titles = [
            u'Hello',
            u'0',
        ]
        for t in normal_titles:
            page = WikiPage.get_by_title(t)
            ss = page.special_sections
            self.assertFalse(u'years' in ss)

    def test_years_section(self):
        page = WikiPage.get_by_title(u'2')
        ss = page.special_sections[u'years']
        self.assertEqual(
            [u'2 BCE', u'1 BCE', u'1', u'2', u'3', u'4', u'5'],
            ss[u'years']
        )

        page = WikiPage.get_by_title(u'2 BCE')
        ss = page.special_sections[u'years']
        self.assertEqual(
            [u'5 BCE', u'4 BCE', u'3 BCE', u'2 BCE', u'1 BCE', u'1', u'2'],
            ss[u'years']
        )


class RedirectionTest(AppEngineTestCase):
    def setUp(self):
        super(RedirectionTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_adding_redirect_should_change_inout_links(self):
        self.update_page(u'[[B]]', u'A')
        self.update_page(u'.redirect C', u'B')

        a = WikiPage.get_by_title(u'A')
        b = WikiPage.get_by_title(u'B')
        c = WikiPage.get_by_title(u'C')
        self.assertEqual({u'Article/relatedTo': [u'C']}, a.outlinks)
        self.assertEqual({}, b.inlinks)
        self.assertEqual({}, b.outlinks)
        self.assertEqual({u'Article/relatedTo': [u'A']}, c.inlinks)

    def test_removing_redirect_should_change_inout_links(self):
        self.update_page(u'[[B]]', u'A')
        self.update_page(u'.redirect C', u'B')
        self.update_page(u'Hello [[D]]', u'B')

        a = WikiPage.get_by_title(u'A')
        b = WikiPage.get_by_title(u'B')
        c = WikiPage.get_by_title(u'C')
        d = WikiPage.get_by_title(u'D')
        self.assertEqual({u'Article/relatedTo': [u'B']}, a.outlinks)
        self.assertEqual({u'Article/relatedTo': [u'A']}, b.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'D']}, b.outlinks)
        self.assertEqual({}, c.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'B']}, d.inlinks)

    def test_changing_redirect_should_change_inout_links(self):
        self.update_page(u'[[B]]', u'A')
        self.update_page(u'.redirect C', u'B')
        self.update_page(u'.redirect D', u'B')

        a = WikiPage.get_by_title(u'A')
        b = WikiPage.get_by_title(u'B')
        c = WikiPage.get_by_title(u'C')
        d = WikiPage.get_by_title(u'D')
        self.assertEqual({u'Article/relatedTo': [u'D']}, a.outlinks)
        self.assertEqual({}, b.inlinks)
        self.assertEqual({}, b.outlinks)
        self.assertEqual({}, c.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'A']}, d.inlinks)

    def test_two_aliases(self):
        self.update_page(u'.redirect C', u'B')
        self.update_page(u'[[C]]', u'A')
        self.update_page(u'[[B]]', u'A')

        a = WikiPage.get_by_title(u'A')
        c = WikiPage.get_by_title(u'C')
        self.assertEqual({u'Article/relatedTo': [u'A']}, c.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'C']}, a.outlinks)

    def test_do_not_allow_redirect_to_self(self):
        self.assertRaises(ValueError, self.update_page, u'.redirect A', u'A')

    def test_do_not_allow_circular_redirect(self):
        self.update_page(u'.redirect B', u'A')
        self.update_page(u'.redirect C', u'B')
        self.assertRaises(ValueError, self.update_page, u'.redirect A', u'C')


class LinkTest(AppEngineTestCase):
    def setUp(self):
        super(LinkTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_nonexisting_page(self):
        a = WikiPage.get_by_title(u'A')
        self.assertEqual({}, a.inlinks)
        self.assertEqual({}, a.outlinks)

    def test_no_links(self):
        page = self.update_page(u'Hello')
        self.assertEqual({}, page.inlinks)
        self.assertEqual({}, page.outlinks)

    def test_links(self):
        a = self.update_page(u'[[B]]', u'A')
        self.assertEqual({}, a.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'B']}, a.outlinks)

        b = WikiPage.get_by_title(u'B')
        self.assertEqual(None, b.updated_at)
        self.assertEqual({u'Article/relatedTo': [u'A']}, b.inlinks)
        self.assertEqual({}, b.outlinks)

    def test_wikiquery(self):
        page = self.update_page(u'[[="Article"]]\n[[=schema:"Article"]]')
        self.assertEqual({}, page.outlinks)

    def test_do_not_display_restricted_links(self):
        a = self.update_page(u'.read ak@gmail.com\n[[B]]', u'A')
        self.assertEqual({}, a.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'B']}, a.outlinks)

        b = WikiPage.get_by_title(u'B')
        self.assertEqual(None, b.updated_at)
        self.assertEqual({}, b.inlinks)
        self.assertEqual({}, b.outlinks)

    def test_get_outlinks(self):
        page = self.update_page(u'[[A]], [[A]], [[Hello World]]')
        self.assertEquals({u'Article/relatedTo': [u'A', u'Hello World']}, page.outlinks)

    def test_rel(self):
        page = self.update_page(u'.schema Person\n[[birthDate::1979]]', u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Person/birthDate': [u'1979']}, page.outlinks)
        self.assertEqual({u'Person/birthDate': [u'A']}, year.inlinks)

    def test_update_rel(self):
        self.update_page(u'[[1979]]', u'A')
        self.update_page(u'.schema Person\n[[birthDate::1979]]', u'A')

        page = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Person/birthDate': [u'1979']}, page.outlinks)
        self.assertEqual({u'Person/birthDate': [u'A']}, year.inlinks)

    def test_add_schema(self):
        self.update_page(u'[[1979]]', u'A')
        self.update_page(u'.schema Book\n[[1979]]', u'A')

        page = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Book/relatedTo': [u'1979']}, page.outlinks)
        self.assertEqual({u'Book/relatedTo': [u'A']}, year.inlinks)

    def test_change_schema(self):
        self.update_page(u'.schema Code\n[[1979]]', u'A')
        self.update_page(u'.schema Book\n[[1979]]', u'A')

        page = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Book/relatedTo': [u'1979']}, page.outlinks)
        self.assertEqual({u'Book/relatedTo': [u'A']}, year.inlinks)

    def test_remove_schema(self):
        self.update_page(u'.schema Code\n[[1979]]', u'A')
        self.update_page(u'[[1979]]', u'A')

        page = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Article/relatedTo': [u'1979']}, page.outlinks)
        self.assertEqual({u'Article/relatedTo': [u'A']}, year.inlinks)

    def test_link_scoretable(self):
        # create outlink
        a = self.update_page(u'[[B]]', u'A')

        # create related link
        a.related_links = {u'D': 0.0}
        a.put()

        # create inlink
        self.update_page(u'[[A]]', u'C')

        scoretable = WikiPage.get_by_title(u'A').link_scoretable
        self.assertEqual([u'C', u'B', u'D'], scoretable.keys())

    def test_link_in_yaml_schema_block(self):
        page = self.update_page(u'.schema Book\n    #!yaml/schema\n    author: Richard Dawkins\n', u'A')
        self.assertEqual({u'Book/author': [u'Richard Dawkins']}, page.outlinks)
        rd = WikiPage.get_by_title(u'Richard Dawkins')
        self.assertEqual({u'Book/author': [u'A']}, rd.inlinks)

    def test_compare_yaml_and_embedded_data(self):
        page1 = self.update_page(u'.schema Book\n    #!yaml/schema\n    datePublished: "1979-03-01"\n', u'A')
        page2 = self.update_page(u'.schema Book\n\n[[datePublished::1979-03-01]]', u'B')
        self.assertEqual(page1.data['datePublished'], page2.data['datePublished'])
        self.assertEqual(page1.outlinks, page2.outlinks)

        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Book/datePublished': [u'A', u'B']}, year.inlinks)


class HashbangTest(AppEngineTestCase):
    def setUp(self):
        super(HashbangTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_no_hashbang(self):
        page = self.update_page(u'    print 1')
        self.assertEqual([], page.hashbangs)

    def test_single_hashbang(self):
        page = self.update_page(u'    #!python\n    print 1')
        self.assertEqual(['python'], page.hashbangs)

    def test_multiple_hashbang(self):
        page = self.update_page(u'    #!python\n    print 1\n\n2\n\n    #!java\n    ;')
        self.assertEqual(['python', 'java'], page.hashbangs)

    def test_inline_hashbang(self):
        page = self.update_page(u'*   Hello ``#!dot/s;There``!')
        self.assertEqual(['dot/s'], page.hashbangs)


class TitleGroupingTest(unittest.TestCase):
    def test_alphabet(self):
        actual = groupby([u'A1', u'a2', u'B'], title_grouper)

        key, titles = actual.next()
        self.assertEqual(u'A', key)
        self.assertEqual([u'A1', u'a2'], list(titles))

        key, titles = actual.next()
        self.assertEqual(u'B', key)
        self.assertEqual([u'B'], list(titles))

    def test_korean(self):
        actual = groupby([u'가나', u'강규영', u'깡', u'나나나'], title_grouper)

        key, titles = actual.next()
        self.assertEqual(u'ㄱ', key)
        self.assertEqual([u'가나', u'강규영', u'깡'], list(titles))

        key, titles = actual.next()
        self.assertEqual(u'ㄴ', key)
        self.assertEqual([u'나나나'], list(titles))


class PageOperationMixinTest(AppEngineTestCase):
    def setUp(self):
        super(PageOperationMixinTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

        self.update_page(u'.pub X\nHello [[There]]', u'Hello')
        self.update_page(u'[[Hello]]', u'Other')

        self.page = WikiPage.get_by_title(u'Hello')
        self.revision = self.page.revisions.fetch()[0]

    def test_rendered_body(self):
        self.assertTrue(self.page.rendered_body.startswith(u'<p>Hello <a class="wikipage" href="/There">There</a></p>\n<h1>Incoming Links <a id="h_ea3d40041db650b8c49e9a81fb17e208" href="#h_ea3d40041db650b8c49e9a81fb17e208" class="caret-target">#</a></h1>\n<h2>Related Articles <a id="h_49b9e0167582ae0274c0d7fe4693a540" href="#h_49b9e0167582ae0274c0d7fe4693a540" class="caret-target">#</a></h2>\n<ul>\n<li><a class="wikipage" href="/Other">Other</a></li>\n</ul>'))
        self.assertTrue(self.revision.rendered_body.startswith(u'<p>Hello <a class="wikipage" href="/There">There</a></p>'))

    def test_is_old_revision(self):
        self.assertEqual(False, self.page.is_old_revision)
        self.assertEqual(True, self.revision.is_old_revision)

    def test_inlinks(self):
        self.assertEqual({u'Article/relatedTo': [u'Other']}, self.page.inlinks)
        self.assertEqual({}, self.revision.inlinks)

    def test_outlinks(self):
        self.assertEqual({u'Article/relatedTo': [u'There']}, self.page.outlinks)
        self.assertEqual({}, self.revision.outlinks)

    def test_related_links(self):
        self.assertEqual({}, self.page.related_links)
        self.assertEqual({}, self.revision.related_links)

    def test_related_links_by_score(self):
        self.assertEqual({}, self.page.related_links_by_score)
        self.assertEqual({}, self.revision.related_links_by_score)

    def test_related_links_by_title(self):
        self.assertEqual({}, self.page.related_links_by_title)
        self.assertEqual({}, self.revision.related_links_by_title)

    def test_metadata(self):
        self.assertEqual(u'X', self.page.metadata['pub'])
        self.assertEqual(u'X', self.revision.metadata['pub'])

    def test_can_read(self):
        self.assertEqual(True, self.page.can_read(None))
        self.assertEqual(True, self.revision.can_read(None))

    def test_can_write(self):
        self.assertEqual(False, self.page.can_write(None))
        self.assertEqual(False, self.revision.can_write(None))

    def test_special_sections(self):
        self.assertEqual({}, self.page.special_sections)
        self.assertEqual({}, self.revision.special_sections)

    def test_itemtype(self):
        self.assertEqual(u'Article', self.page.itemtype)
        self.assertEqual(u'Article', self.revision.itemtype)

    def test_itemtype_url(self):
        self.assertEqual(u'http://schema.org/Article', self.page.itemtype_url)
        self.assertEqual(u'http://schema.org/Article', self.revision.itemtype_url)


class UserPreferencesTest(AppEngineTestCase):
    def setUp(self):
        super(UserPreferencesTest, self).setUp()
        self.user = users.User('user@example.com')

    def test_get_by_user(self):
        prefs = UserPreferences.get_by_user(self.user)
        self.assertEquals(None, prefs.userpage_title)

        prefs.userpage_title = u'김경수'
        prefs.put()
        self.assertEquals(u'김경수', UserPreferences.get_by_user(self.user).userpage_title)


class WikiPageDeleteTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageDeleteTest, self).setUp()
        self.login('a@x.com', 'a')

        self.update_page(u'Hello [[B]]', u'A')
        self.update_page(u'Hello [[A]]', u'B')

        # reload
        self.pagea = WikiPage.get_by_title(u'A')
        self.pageb = WikiPage.get_by_title(u'B')

    def test_deleted(self):
        self.login('a@x.com', 'a', is_admin=True)
        self.pagea.delete(users.get_current_user())

        self.pagea = WikiPage.get_by_title(u'A')
        self.assertEquals(None, self.pagea.modifier)
        self.assertEquals(u'', self.pagea.body)
        self.assertEquals(0, self.pagea.revision)

    def test_only_admin_can_perform_delete(self):
        self.login('a@x.com', 'a')
        self.assertRaises(RuntimeError, self.pagea.delete, users.get_current_user())

    def test_revisions_should_be_deleted_too(self):
        self.login('a@x.com', 'a', is_admin=True)
        self.pagea.delete(users.get_current_user())
        self.assertEqual(0, self.pagea.revisions.count())

    def test_in_out_links(self):
        self.login('a@x.com', 'a', is_admin=True)

        self.pagea.delete(users.get_current_user())
        self.pageb = WikiPage.get_by_title(u'B')
        self.assertEquals(1, len(self.pagea.inlinks))
        self.assertEquals(0, len(self.pagea.outlinks))
        self.assertEquals(0, len(self.pageb.inlinks))
        self.assertEquals(1, len(self.pageb.outlinks))

    def test_delete_twice(self):
        self.login('a@x.com', 'a', is_admin=True)

        self.pagea.delete(users.get_current_user())
        self.pagea = WikiPage.get_by_title(u'A')
        self.pagea.delete(users.get_current_user())

    def test_delete_and_create(self):
        self.login('a@x.com', 'a', is_admin=True)

        self.pagea.delete(users.get_current_user())
        self.pagea = WikiPage.get_by_title(u'A')
        self.pagea.update_content(u'Hello', 0, user=self.get_cur_user())
        self.assertEquals(1, self.pagea.revision)

    def test_delete_and_redirection_1(self):
        self.update_page(u'.redirect C', u'B')
        self.update_page(u'Hello [[A]]', u'C')

        self.login('a@x.com', 'a', is_admin=True)
        WikiPage.get_by_title(u'A').delete(users.get_current_user())

        self.pagea = WikiPage.get_by_title(u'A')
        self.pagec = WikiPage.get_by_title(u'C')

        self.assertEquals(1, len(self.pagea.inlinks))
        self.assertEquals(0, len(self.pagea.outlinks))
        self.assertEquals(0, len(self.pagec.inlinks))
        self.assertEquals(1, len(self.pagec.outlinks))

    def test_delete_and_redirection_2(self):
        self.update_page(u'.redirect C', u'B')
        self.update_page(u'Hello [[A]]', u'C')

        self.login('a@x.com', 'a', is_admin=True)
        WikiPage.get_by_title(u'B').delete(users.get_current_user())

        self.pagea = WikiPage.get_by_title(u'A')
        self.pageb = WikiPage.get_by_title(u'B')
        self.pagec = WikiPage.get_by_title(u'C')

        self.assertEquals(1, len(self.pagea.inlinks))
        self.assertEquals(1, len(self.pagea.outlinks))
        self.assertEquals(1, len(self.pageb.inlinks))
        self.assertEquals(0, len(self.pageb.outlinks))
        self.assertEquals(0, len(self.pagec.inlinks))
        self.assertEquals(1, len(self.pagec.outlinks))


class WikiPageHierarchyTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageHierarchyTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_no_hierarchy(self):
        page = WikiPage.get_by_title(u'GEB')
        self.assertEqual(
            [
                (u'GEB', u'GEB')
            ],
            page.paths
        )

    def test_hierarchy(self):
        page = WikiPage.get_by_title(u'GEB/Chapter 1/Memo')
        self.assertEqual(
            [
                (u'GEB', u'GEB'),
                (u'GEB/Chapter 1', u'Chapter 1'),
                (u'GEB/Chapter 1/Memo', u'Memo'),
            ],
            page.paths
        )

    def test_ancestors_should_be_regarded_as_outlinks(self):
        page = self.update_page(u'Hello [[There]]', u'GEB/Chapter 1/Memo')
        self.assertEqual([u'GEB', u'GEB/Chapter 1', u'There'], page.outlinks['Article/relatedTo'])
        self.assertEqual({u'Article/relatedTo': [u'GEB/Chapter 1/Memo']}, WikiPage.get_by_title(u'GEB').inlinks)

    def test_delete(self):
        self.login('ak@gmail.com', 'ak', is_admin=True)

        memo = self.update_page(u'Hello', u'GEB/Chapter 1/Memo')
        memo.delete(self.get_cur_user())

        self.assertEqual({}, WikiPage.get_by_title(u'GEB').inlinks)
        self.assertEqual({}, WikiPage.get_by_title(u'GEB/Chapter 1').inlinks)


class WikiPageBugsTest(AppEngineTestCase):
    def test_remove_acl_and_link_at_once_caused_an_error(self):
        self.login('ak@gmail.com', 'ak')
        try:
            self.update_page(u'.read ak@gmail.com\n[[B]]', u'A')
            self.update_page(u'Hello', u'A')
        except AssertionError:
            self.fail()
