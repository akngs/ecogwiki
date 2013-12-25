# -*- coding: utf-8 -*-
from tests import AppEngineTestCase
from models import WikiPage


class DefaultBlogPublishTest(AppEngineTestCase):
    def setUp(self):
        super(DefaultBlogPublishTest, self).setUp()

    def test_first_publish(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0)
        self.assertEqual(0, len(WikiPage.get_published_posts(None, 20)))

        page.update_content(u'.pub\nHello', 1)

        self.assertIsNotNone(page.published_at)
        self.assertIsNone(page.published_to)
        self.assertEqual(1, len(WikiPage.get_published_posts(None, 20)))

    def test_second_publish(self):
        page1 = WikiPage.get_by_title(u'Hello 1')
        page1.update_content(u'.pub\nHello 1', 0)

        page2 = WikiPage.get_by_title(u'Hello 2')
        page2.update_content(u'.pub\nHello 2', 0)

        posts = WikiPage.get_published_posts(None, 20)

        self.assertEqual(2, len(posts))
        self.assertEqual(page2.title, posts[1].newer_title)
        self.assertEqual(page1.title, posts[0].older_title)


class DefaultBlogUnpublishTest(AppEngineTestCase):
    def setUp(self):
        super(DefaultBlogUnpublishTest, self).setUp()

        page1 = WikiPage.get_by_title(u'Hello 1')
        page1.update_content(u'.pub\nHello 1', 0)

        page2 = WikiPage.get_by_title(u'Hello 2')
        page2.update_content(u'.pub\nHello 2', 0)

        page3 = WikiPage.get_by_title(u'Hello 3')
        page3.update_content(u'.pub\nHello 3', 0)

    def test_unpublish_middle(self):
        middle = WikiPage.get_by_title(u'Hello 2')
        middle.update_content(u'Hello 2', 1)

        newer, older = WikiPage.get_published_posts(None, 20)

        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)

    def test_unpublish_oldest(self):
        oldest = WikiPage.get_by_title(u'Hello 1')
        oldest.update_content(u'Hello 1', 1)

        newer, older = WikiPage.get_published_posts(None, 20)

        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 2', newer.older_title)

    def test_unpublish_newest(self):
        newest = WikiPage.get_by_title(u'Hello 3')
        newest.update_content(u'Hello 3', 1)

        newer, older = WikiPage.get_published_posts(None, 20)

        self.assertEqual(u'Hello 2', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)


class CustomBlogTest(AppEngineTestCase):
    def setUp(self):
        super(CustomBlogTest, self).setUp()

    def test_publish(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub Posts\nHello', 0)
        self.assertIsNotNone(page.published_at)
        self.assertEqual('Posts', page.published_to)
        self.assertEqual(1, len(WikiPage.get_published_posts('Posts', 20)))

    def test_specify_page_to_published_page(self):
        # .pub -> .pub BBS
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub\nHello', 0)
        page.update_content(u'.pub BBS\nHello', 1)
        self.assertIsNotNone(page.published_at)
        self.assertEqual('BBS', page.published_to)

    def test_change_page_of_published_page(self):
        # .pub BBS1 -> .pub BBS2
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub BBS1\nHello', 0)
        page.update_content(u'.pub BBS2\nHello', 1)
        self.assertIsNotNone(page.published_at)
        self.assertEqual('BBS2', page.published_to)

    def test_remove_page_of_published_page(self):
        # .pub BBS -> .pub
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub BBS\nHello', 0)
        page.update_content(u'.pub\nHello', 1)
        self.assertIsNotNone(page.published_at)
        self.assertEqual(None, page.published_to)

    def test_unpublish_published_page(self):
        # .pub BBS -> (null)
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'.pub BBS\nHello', 0)
        page.update_content(u'Hello', 1)
        self.assertIsNone(page.published_at)
        self.assertEqual(None, page.published_to)


class MultipleCustomBlogsTest(AppEngineTestCase):
    def setUp(self):
        super(MultipleCustomBlogsTest, self).setUp()

        self.b1p1 = WikiPage.get_by_title(u'b1p1')
        self.b1p1.update_content(u'.pub B1', 0)
        self.b2p1 = WikiPage.get_by_title(u'b2p1')
        self.b2p1.update_content(u'.pub B2', 0)
        self.b1p2 = WikiPage.get_by_title(u'b1p2')
        self.b1p2.update_content(u'.pub B1', 0)
        self.b2p2 = WikiPage.get_by_title(u'b2p2')
        self.b2p2.update_content(u'.pub B2', 0)

    def test_older_newer_isolation(self):
        b1p1 = WikiPage.get_by_title(u'b1p1')
        b1p2 = WikiPage.get_by_title(u'b1p2')
        b2p1 = WikiPage.get_by_title(u'b2p1')
        b2p2 = WikiPage.get_by_title(u'b2p2')

        self.assertEqual('b1p2', b1p1.newer_title)
        self.assertEqual('b1p1', b1p2.older_title)
        self.assertEqual('b2p2', b2p1.newer_title)
        self.assertEqual('b2p1', b2p2.older_title)
