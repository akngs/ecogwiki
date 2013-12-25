# -*- coding: utf-8 -*-
import main
import cache
import unittest2 as unittest
from itertools import groupby
from tests import AppEngineTestCase
from google.appengine.api import users
from markdownext.md_wikilink import parse_wikilinks
from models import md, WikiPage, UserPreferences, title_grouper, ConflictError


class WikiPagePartialUpdateTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPagePartialUpdateTest, self).setUp()

    def test_check_checkbox(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'[ ] Item A\n[x] Item B', 0)
        page.update_content(u'1', 1, partial='checkbox[0]')

        self.assertEqual(u'[x] Item A\n[x] Item B', page.body)
        self.assertEqual(2, page.revision)
        
        page.update_content(u'0', 1, partial='checkbox[1]')
        self.assertEqual(u'[x] Item A\n[ ] Item B', page.body)
        self.assertEqual(3, page.revision)


class WikiPageUpdateTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageUpdateTest, self).setUp()

    def test_should_update_acls(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.read test1\n.write test2\nHello', 0)
        self.assertEqual(u'test1', page.acl_read)
        self.assertEqual(u'test2', page.acl_write)

        page.update_content(u'Hello', 1)
        self.assertEqual(u'', page.acl_read)
        self.assertEqual(u'', page.acl_write)

    def test_should_create_revision(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0)
        page.update_content(u'Hello 2', 1)

        revs = list(page.revisions)
        self.assertEqual(2, len(revs))
        self.assertEqual(u'Hello', revs[0].body)
        self.assertEqual(u'Hello 2', revs[1].body)

    def test_should_not_create_revision_if_content_is_not_changed(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0)
        page.update_content(u'Hello', 0)

        revs = list(page.revisions)
        self.assertEqual(1, len(revs))
        self.assertEqual(u'Hello', revs[0].body)

    def test_automerge(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'A\nB\nC', 0)

        # remove B
        page.update_content(u'A\nC', 1)
        # append D
        page.update_content(u'A\nB\nC\nD', 1)

        # should be merged
        page = WikiPage.get_by_title(u'Hello')
        self.assertEqual(u'A\nC\nD', page.body)
        self.assertEqual(3, page.revision)

        revs = list(page.revisions)
        self.assertEqual(3, len(revs))

    def test_conflict(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'A\nB\nC', 0)

        # update second line
        page.update_content(u'A\nD\nC', 1)

        # update second line concurrently
        self.assertRaises(ConflictError, page.update_content, u'A\nE\nC', 1)

        # page should not be updated
        page = WikiPage.get_by_title(u'Hello')
        self.assertEqual(u'A\nD\nC', page.body)
        self.assertEqual(2, page.revision)

        revs = list(page.revisions)
        self.assertEqual(2, len(revs))

    def test_duplicated_headings(self):
        page = WikiPage.get_by_title(u'Hello')
        self.assertRaises(ValueError, page.update_content, u'# A\n# A', 0)

    def test_malformed_yaml_schema(self):
        page = WikiPage.get_by_title(u'Hello')
        self.assertRaises(ValueError, page.update_content, u'.schema Book\n\n    #!yaml/schema\n    y: [1, 2\n', 0)

    def test_invalid_yaml_schema(self):
        page = WikiPage.get_by_title(u'Hello')
        self.assertRaises(ValueError, page.update_content, u'.schema Book\n\n    #!yaml/schema\n    y\n', 0)


class WikiPageMetadataParserTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageMetadataParserTest, self).setUp()
        self.default_md = {
            'content-type': 'text/x-markdown',
            'schema': 'Article',
        }

    def test_normal(self):
        page = WikiPage.get_by_title(u'Hello')
        expected = {
            u'hello': u'a b c',
            u'x': None,
            u'z': u'what?',
        }
        expected.update(self.default_md)
        actual = page.parse_metadata(u'.hello a b c\n.x\n.z what?\nblahblah')
        self.assertEqual(expected, actual)

    def test_empty_string(self):
        page = WikiPage.get_by_title(u'Hello')
        expected = {}
        expected.update(self.default_md)
        actual = page.parse_metadata(u'')
        self.assertEqual(expected, actual)

    def test_no_metadata(self):
        page = WikiPage.get_by_title(u'Hello')
        expected = {}
        expected.update(self.default_md)
        actual = page.parse_metadata(u'Hello\nThere')
        self.assertEqual(expected, actual)

    def test_get_body_only(self):
        expected = u'blahblah'
        actual = WikiPage.remove_metadata(u'.hello a b c\n.x what?\nblahblah')
        self.assertEqual(expected, actual)

    def test_line_starts_with_a_dot(self):
        expected = u'Hello\n.There'
        actual = WikiPage.remove_metadata(u'Hello\n.There')
        self.assertEqual(expected, actual)


class WikiPageWikiLinkParserTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual({u'Article/relatedTo': [u'A']},
                         parse_wikilinks('Article', u'[[A]]'))

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
                         parse_wikilinks('Article',
                                         u'[[birthDate::1979-03-27 BCE]]'))
        self.assertEqual({u'Article/relatedTo': [u'A'],
                          u'Article/author': [u'B']},
                         parse_wikilinks('Article', u'[[A]] [[author::B]]'))

    def test_wikiquery(self):
        self.assertEqual({}, parse_wikilinks('Article', u'[[="Hello"]]'))
        self.assertEqual({}, parse_wikilinks('Article', u'[[=schema:"Article"]]'))


class WikiPageRenderingTest(unittest.TestCase):
    def test_strikethrough(self):
        actual = md.convert(u'Hello ~~AK~~?')
        expected = u'<p>Hello <strike>AK</strike>?</p>'
        self.assertEqual(expected, actual)

    def test_checkbox(self):
        actual = md.convert(u'[ ] Hello [x] There')
        expected = u'<p><input type="checkbox" /> Hello <input checked="checked" type="checkbox" /> There</p>'
        self.assertEqual(expected, actual)


class WikiPageWikilinkRenderingTest(unittest.TestCase):
    def test_plain(self):
        actual = md.convert(u'[[heyyou]]')
        expected = u'<p><a class="wikipage" href="/heyyou">heyyou</a></p>'
        self.assertEqual(expected, actual)

    def test_space(self):
        actual = md.convert(u'[[Hey you]]')
        expected = u'<p><a class="wikipage" href="/Hey_you">Hey you</a></p>'
        self.assertEqual(expected, actual)

    def test_special_character(self):
        actual = md.convert(u'[[You&I]]')
        expected = u'<p><a class="wikipage" href="/You%26I">You&amp;I</a></p>'
        self.assertEqual(expected, actual)

    def test_unicode_character(self):
        actual = md.convert(u'[[가]]')
        expected = u'<p><a class="wikipage" href="/%EA%B0%80">가</a></p>'
        self.assertEqual(expected, actual)

    def test_possible_conflict_with_plain_link(self):
        actual = md.convert(u'[[Hello]](there)')
        expected = u'<p><a class="wikipage" href="/Hello">Hello</a>(there)</p>'
        self.assertEqual(expected, actual)

    def test_yyyymmdd(self):
        actual = md.convert(u'[[1979-03-05]]')
        expected = u'<p><time datetime="1979-03-05">' \
                   u'<a class="wikipage" href="/1979">1979</a>' \
                   u'<span>-</span>' \
                   u'<a class="wikipage" href="/March_5">03-05</a>' \
                   u'</time></p>'
        self.assertEqual(expected, actual)

    def test_yyyymmxx(self):
        actual = md.convert(u'[[1979-03-??]]')
        expected = u'<p><time datetime="1979-03-??">' \
                   u'<a class="wikipage" href="/1979">1979</a>' \
                   u'<span>-</span>' \
                   u'<a class="wikipage" href="/March">03-??</a>' \
                   u'</time></p>'
        self.assertEqual(expected, actual)

    def test_yyyyxxxx(self):
        actual = md.convert(u'[[1979-??-??]]')
        expected = u'<p><time datetime="1979-??-??">' \
                   u'<a class="wikipage" href="/1979">1979</a>' \
                   u'<span>-</span>' \
                   u'<span>??-??</span>' \
                   u'</time></p>'
        self.assertEqual(expected, actual)

    def test_yyyymmdd_bce(self):
        actual = md.convert(u'[[1979-03-05 BCE]]')
        expected = u'<p><time datetime="1979-03-05 BCE">' \
                   u'<a class="wikipage" href="/1979_BCE">1979</a>' \
                   u'<span>-</span>' \
                   u'<a class="wikipage" href="/March_5">03-05</a>' \
                   u'<span> BCE</span></time></p>'
        self.assertEqual(expected, actual)

    def test_url(self):
        actuals = [
            u'http://x.co',
            u'(http://x.co)',
            u'http://x.co에',
            u'http://x.co?y',
            u'codeRepository::http://x.co',
            u'a@x.com',
            u'a@x.kr에',
            u'http://www.youtube.com/watch?v=w5gmK-ZXIMQ',
            u'http://vimeo.com/1747316',
        ]
        expecteds = [
            u'<p><a class="plainurl" href="http://x.co">http://x.co</a></p>',
            u'<p>(<a class="plainurl" href="http://x.co">http://x.co</a>)</p>',
            u'<p><a class="plainurl" href="http://x.co">http://x.co</a>에</p>',
            u'<p><a class="plainurl" href="http://x.co?y">http://x.co?y</a></p>',
            u'<p><a class="plainurl" href="http://x.co" '
            u'itemprop="codeRepository">http://x.co</a></p>',
            u'<p><a class="email" href="mailto:a@x.com">a@x.com</a></p>',
            u'<p><a class="email" href="mailto:a@x.kr">a@x.kr</a>에</p>',
            u'<p>\n<div class="video youtube">\n<iframe allowfullscreen="true" frameborder="0" height="390" src="http://www.youtube.com/embed/w5gmK-ZXIMQ" width="640"></iframe>\n</div>\n</p>',
            u'<p>\n<div class="video vimeo">\n<iframe allowfullscreen="true" frameborder="0" height="281" src="http://player.vimeo.com/video/1747316" width="500"></iframe>\n</div>\n</p>',
        ]

        for e, a in zip(expecteds, actuals):
            self.assertEqual(e, md.convert(a))

    def test_rel(self):
        actual = md.convert(u'[[sameAs::heyyou]]')
        expected = u'<p><a class="wikipage" href="/heyyou" itemprop="sameAs">' \
                   u'heyyou</a></p>'
        self.assertEqual(expected, actual)

        actual = md.convert(u'[[birthDate::1979-03-05 BCE]]')
        expected = u'<p><time datetime="1979-03-05 BCE" itemprop="birthDate">' \
                   u'<a class="wikipage" href="/1979_BCE">1979</a>' \
                   u'<span>-</span>' \
                   u'<a class="wikipage" href="/March_5">03-05</a>' \
                   u'<span> BCE</span></time></p>'
        self.assertEqual(expected, actual)


class HTMLRenderingTest(unittest.TestCase):
    def test_div(self):
        actual = md.convert(u'<div class="test">He*l*lo</div>\nWo*r*ld')
        expected = u'<div class="test">He*l*lo</div>\n\n<p>Wo<em>r</em>ld</p>'
        self.assertEqual(expected, actual)


class SchemaItemPropertyRenderingTest(unittest.TestCase):
    def test_isbn(self):
        actual = md.convert(u'{{isbn::0618680004}}')
        expected = u'<p><a class="isbn" href="http://www.amazon.com/gp/' \
                   u'product/0618680004" itemprop="isbn">0618680004</a></p>'
        self.assertEqual(expected, actual)

    def test_isbn_kr(self):
        actual = md.convert(u'{{isbn::8936437267}}')
        expected = u'<p><a class="isbn" href="http://www.aladin.co.kr/' \
                   u'shop/wproduct.aspx?ISBN=' \
                   u'9788936437267" itemprop="isbn">9788936437267</a></p>'
        self.assertEqual(expected, actual)

    def test_isbn13_kr(self):
        actual = md.convert(u'{{isbn::9788936437267}}')
        expected = u'<p><a class="isbn" href="http://www.aladin.co.kr/' \
                   u'shop/wproduct.aspx?ISBN=' \
                   u'9788936437267" itemprop="isbn">9788936437267</a></p>'
        self.assertEqual(expected, actual)

    def test_generic_key_value(self):
        actual = md.convert(u'{{hello::world from ak}}')
        expected = u'<p><span itemprop="hello">world from ak</span></p>'
        self.assertEqual(expected, actual)

    def test_class(self):
        actual = md.convert(u'{{.hello::world from ak}}')
        expected = u'<p><span class="hello">world from ak</span></p>'
        self.assertEqual(expected, actual)


class WikiTitleToPathConvertTest(AppEngineTestCase):
    def setUp(self):
        super(WikiTitleToPathConvertTest, self).setUp()

    def test_title_to_path(self):
        self.assertEqual('Hello_World', WikiPage.title_to_path(u'Hello World'))
        self.assertEqual('A%26B', WikiPage.title_to_path(u'A&B'))
        self.assertEqual('%EA%B0%80', WikiPage.title_to_path(u'가'))

    def test_path_to_title(self):
        self.assertEqual(u'Hello World', WikiPage.path_to_title('Hello_World'))
        self.assertEqual(u'A&B', WikiPage.path_to_title('A%26B'))
        self.assertEqual(u'가', WikiPage.path_to_title('%EA%B0%80'))


class WikiYamlParserTest(AppEngineTestCase):
    def setUp(self):
        super(WikiYamlParserTest, self).setUp()

    def test_empty_page(self):
        self.assertEqual(main.DEFAULT_CONFIG, WikiPage.get_config())


class WikiPageGetConfigTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageGetConfigTest, self).setUp()
        self.config_page = WikiPage.get_by_title('.config')
        self.config_page.update_content(u'''
          admin:
            email: janghwan@gmail.com
          service:
            default_permissions:
              read: [all]
              write: [login]
        ''', 0)

    def test_empty_config_page(self):
        config_page = WikiPage.get_by_title('.config')
        config_page.update_content('', 1)

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


class WikiPageRelatedPageUpdatingTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageRelatedPageUpdatingTest, self).setUp()

    def test_update_related_links(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'[[B]]', 0, dont_defer=True)

        b = WikiPage.get_by_title(u'B')
        b.update_content(u'[[C]]', 0, dont_defer=True)

        c = WikiPage.get_by_title(u'C')
        c.update_content(u'[[D]]', 0, dont_defer=True)

        a.update_related_links()
        a.put()

        self.assertEqual({u'C': 0.025, u'D': 0.0125}, a.related_links)

    def test_redirect(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'[[B]]', 0, dont_defer=True)
        b = WikiPage.get_by_title(u'B')
        b.update_content(u'.redirect C', 0, dont_defer=True)
        c = WikiPage.get_by_title(u'C')
        c.update_content(u'[[D]]', 0, dont_defer=True)
        d = WikiPage.get_by_title(u'D')
        d.update_content(u'Destination', 0, dont_defer=True)

        a.update_related_links()
        self.assertTrue(u'D' in a.related_links)


class WikiPageSimilarTitlesTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageSimilarTitlesTest, self).setUp()

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


class WikiPageDescriptionTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageDescriptionTest, self).setUp()

    def test_try_newline(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello\nWorld', 0)
        self.assertEqual(u'Hello', page.make_description(20))

    def test_try_period(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hi. Hello. World. Sentences.', 0)
        self.assertEqual(u'Hi. Hello. World.', page.make_description(20))

    def test_cut_off(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hi Hello World Sentences.', 0)
        self.assertEqual(u'Hi Hello World Se...', page.make_description(20))

    def test_should_ignore_metadata(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub\n\nHello', 0)
        self.assertEqual(u'Hello', page.make_description(20))

    def test_should_ignore_yaml_schema_block(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.schema Book\n    #!yaml/schema\n    author: A\n\nHello', 0)
        self.assertEqual(u'Hello', page.make_description(20))


class WikiPageSpecialTitlesTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageSpecialTitlesTest, self).setUp()

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

    def test_adding_redirect_should_change_inout_links(self):
        WikiPage.get_by_title(u'A').update_content(u'[[B]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'B').update_content(u'.redirect C', 0, dont_defer=True)

        a = WikiPage.get_by_title(u'A')
        b = WikiPage.get_by_title(u'B')
        c = WikiPage.get_by_title(u'C')
        self.assertEqual({u'Article/relatedTo': [u'C']}, a.outlinks)
        self.assertEqual({}, b.inlinks)
        self.assertEqual({}, b.outlinks)
        self.assertEqual({u'Article/relatedTo': [u'A']}, c.inlinks)

    def test_removing_redirect_should_change_inout_links(self):
        WikiPage.get_by_title(u'A').update_content(u'[[B]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'B').update_content(u'.redirect C', 0, dont_defer=True)
        WikiPage.get_by_title(u'B').update_content(u'Hello [[D]]', 1, dont_defer=True)

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
        WikiPage.get_by_title(u'A').update_content(u'[[B]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'B').update_content(u'.redirect C', 0, dont_defer=True)
        WikiPage.get_by_title(u'B').update_content(u'.redirect D', 1, dont_defer=True)

        # flush thread-local cache
        cache.prc.flush_all()

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
        WikiPage.get_by_title(u'B').update_content(u'.redirect C', 0, dont_defer=True)
        WikiPage.get_by_title(u'A').update_content(u'B, [[C]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'A').update_content(u'[[B]]', 1, dont_defer=True)
        a = WikiPage.get_by_title(u'A')
        c = WikiPage.get_by_title(u'C')
        self.assertEqual({u'Article/relatedTo': [u'A']}, c.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'C']}, a.outlinks)

    def test_do_not_allow_circular_redirect(self):
        page = WikiPage.get_by_title(u'A')
        self.assertRaises(ValueError, page.update_content, u'.redirect A', 0, dont_defer=True)


class WikiPageLinksTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageLinksTest, self).setUp()

    def test_nonexisting_page(self):
        a = WikiPage.get_by_title(u'A')
        self.assertEqual({}, a.inlinks)
        self.assertEqual({}, a.outlinks)

    def test_no_links(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'Hello', 0)

        a = WikiPage.get_by_title(u'A')
        self.assertEqual({}, a.inlinks)
        self.assertEqual({}, a.outlinks)

    def test_links(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'[[B]]', 0, dont_defer=True)

        a = WikiPage.get_by_title(u'A')
        b = WikiPage.get_by_title(u'B')

        self.assertEqual({}, a.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'B']}, a.outlinks)

        self.assertEqual(None, b.updated_at)
        self.assertEqual({u'Article/relatedTo': [u'A']}, b.inlinks)
        self.assertEqual({}, b.outlinks)

    def test_wikiquery(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'[[="Article"]]\n[[=schema:"Article"]]', 0, dont_defer=True)
        self.assertEqual({}, a.outlinks)

    def test_do_not_display_restricted_links(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'.read a@x.com\n[[B]]', 0, dont_defer=True)

        a = WikiPage.get_by_title(u'A')
        b = WikiPage.get_by_title(u'B')

        self.assertEqual({}, a.inlinks)
        self.assertEqual({u'Article/relatedTo': [u'B']}, a.outlinks)

        self.assertEqual(None, b.updated_at)
        self.assertEqual({}, b.inlinks)
        self.assertEqual({}, b.outlinks)

    def test_get_outlinks(self):
        page = WikiPage.get_by_title(u'Test')
        page.update_content(u'[[A]], [[A]], [[Hello World]]', 0, dont_defer=True)
        links = page.outlinks
        self.assertEquals({u'Article/relatedTo': [u'A', u'Hello World']}, links)

    def test_rel(self):
        WikiPage.get_by_title(u'A').update_content(u'[[birthDate::1979]]', 0, dont_defer=True)
        a = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Article/birthDate': [u'1979']}, a.outlinks)
        self.assertEqual({u'Article/birthDate': [u'A']}, year.inlinks)

    def test_update_rel(self):
        WikiPage.get_by_title(u'A').update_content(u'[[1979]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'A').update_content(u'[[birthDate::1979]]', 1, dont_defer=True)
        a = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Article/birthDate': [u'1979']}, a.outlinks)
        self.assertEqual({u'Article/birthDate': [u'A']}, year.inlinks)

    def test_add_schema(self):
        WikiPage.get_by_title(u'A').update_content(u'[[1979]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'A').update_content(u'.schema Book\n[[1979]]', 1, dont_defer=True)

        a = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Book/relatedTo': [u'1979']}, a.outlinks)
        self.assertEqual({u'Book/relatedTo': [u'A']}, year.inlinks)

    def test_change_schema(self):
        WikiPage.get_by_title(u'A').update_content(u'.schema Code\n[[1979]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'A').update_content(u'.schema Book\n[[1979]]', 1, dont_defer=True)

        a = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Book/relatedTo': [u'1979']}, a.outlinks)
        self.assertEqual({u'Book/relatedTo': [u'A']}, year.inlinks)

    def test_remove_schema(self):
        WikiPage.get_by_title(u'A').update_content(u'.schema Code\n[[1979]]', 0, dont_defer=True)
        WikiPage.get_by_title(u'A').update_content(u'[[1979]]', 1, dont_defer=True)

        a = WikiPage.get_by_title(u'A')
        year = WikiPage.get_by_title(u'1979')
        self.assertEqual({u'Article/relatedTo': [u'1979']}, a.outlinks)
        self.assertEqual({u'Article/relatedTo': [u'A']}, year.inlinks)

    def test_unknown_schema(self):
        page = WikiPage.get_by_title(u'A')
        self.assertRaises(ValueError, page.update_content, u'.schema WhatTheHell\n[[1979]]', 0)

    def test_link_scoretable(self):
        page = WikiPage.get_by_title(u'A')

        # create outlink
        page.update_content(u'[[B]]', 0, dont_defer=True)

        # create related link
        page.related_links = {u'D': 0.0}
        page.put()

        # create inlink
        WikiPage.get_by_title(u'C').update_content(u'[[A]]', 0, dont_defer=True)

        scoretable = WikiPage.get_by_title(u'A').link_scoretable
        self.assertEqual([u'C', u'B', u'D'], scoretable.keys())

    def test_link_in_yaml_schema_block(self):
        page = WikiPage.get_by_title(u'A')
        page.update_content(u'.schema Book\n    #!yaml/schema\n    author: Richard Dawkins\n', 0, dont_defer=True)

        page = WikiPage.get_by_title(u'A')
        self.assertEqual({u'Book/author': [u'Richard Dawkins']}, page.outlinks)

        rd = WikiPage.get_by_title(u'Richard Dawkins')
        self.assertEqual({u'Book/author': [u'A']}, rd.inlinks)

    def test_compare_yaml_and_embedded_data(self):
        page1 = WikiPage.get_by_title(u'A')
        page1.update_content(u'.schema Book\n    #!yaml/schema\n    datePublished: "1979-03-01"\n', 0)
        page2 = WikiPage.get_by_title(u'B')
        page2.update_content(u'.schema Book\n\n[[datePublished::1979-03-01]]', 0)

        self.assertEqual(page1.data['datePublished'], page2.data['datePublished'])
        self.assertEqual(page1.outlinks, page2.outlinks)

    def test_update_link_in_yaml_schema_block(self):
        page = WikiPage.get_by_title(u'A')
        page.update_content(u'.schema Book\n    #!yaml/schema\n    author: Richard Dawkins\n', 0, dont_defer=True)
        page.update_content(u'.schema Book\n    #!yaml/schema\n    author: Edward Wilson\n', 1, dont_defer=True)

        page = WikiPage.get_by_title(u'A')
        self.assertEqual({u'Book/author': [u'Edward Wilson']}, page.outlinks)

        rd = WikiPage.get_by_title(u'Richard Dawkins')
        self.assertEqual({}, rd.inlinks)

        ew = WikiPage.get_by_title(u'Edward Wilson')
        self.assertEqual({u'Book/author': [u'A']}, ew.inlinks)

    def test_should_not_treat_isbn_in_schema_block_as_a_link(self):
        page = WikiPage.get_by_title(u'A')
        page.update_content(u'.schema Book\n    #!yaml/schema\n    isbn: "123456789"\n', 0)

        page = WikiPage.get_by_title(u'A')
        self.assertEqual({}, page.outlinks)


class WikiPageHashbang(AppEngineTestCase):
    def setUp(self):
        super(WikiPageHashbang, self).setUp()

    def test_no_hashbang(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'    print 1', 0)
        self.assertEqual([], a.hashbangs)

    def test_single_hashbang(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'    #!python\n    print 1', 0)
        self.assertEqual(['python'], a.hashbangs)

    def test_multiple_hashbang(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'    #!python\n    print 1\n\n2\n\n    #!java\n    ;', 0)
        self.assertEqual(['python', 'java'], a.hashbangs)

    def test_inline_hashbang(self):
        a = WikiPage.get_by_title(u'A')
        a.update_content(u'*   Hello ``#!dot/s;There``!', 0)
        self.assertEqual(['dot/s'], a.hashbangs)


class WikiPageTitleGroupingTest(unittest.TestCase):
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

        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub X\nHello [[There]]', 0, u'', dont_defer=True)
        page2 = WikiPage.get_by_title(u'Other')
        page2.update_content(u'[[Hello]]', 0, u'', dont_defer=True)
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


class WikiPageBugsTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageBugsTest, self).setUp()

    def test_remove_acl_and_link_at_once_caused_an_error(self):
        try:
            WikiPage.get_by_title(u'A').update_content(u'.read jania902@gmail.com\n'
                                                       u'[[B]]', 0)
            WikiPage.get_by_title(u'A').update_content(u'Hello', 1)
        except AssertionError:
            self.fail()


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

        self.pagea = WikiPage.get_by_title(u'A')
        self.pagea.update_content(u'Hello [[B]]', 0, dont_defer=True)
        self.pageb = WikiPage.get_by_title(u'B')
        self.pageb.update_content(u'Hello [[A]]', 0, dont_defer=True)

        # reload
        self.pagea = WikiPage.get_by_title(u'A')
        self.pageb = WikiPage.get_by_title(u'B')

    def test_should_be_deleted(self):
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
        self.pagea.update_content(u'Hello', 0)
        self.assertEquals(1, self.pagea.revision)


class WikiPageHierarchyTest(AppEngineTestCase):
    def setUp(self):
        super(WikiPageHierarchyTest, self).setUp()

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
        page = WikiPage.get_by_title(u'GEB/Chapter 1/Memo')
        page.update_content(u'Hello [[There]]', 0, dont_defer=True)
        self.assertEqual([u'GEB', u'GEB/Chapter 1', u'There'], page.outlinks['Article/relatedTo'])
