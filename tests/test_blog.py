# -*- coding: utf-8 -*-
from tests import AppEngineTestCase
from models import WikiPage


class DefaultBlogPublishTest(AppEngineTestCase):
    def setUp(self):
        super(DefaultBlogPublishTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_first_publish(self):
        self.update_page(u'Hello', u'Hello')
        self.assertEqual(0, len(WikiPage.get_posts_of(None)))

        page = self.update_page(u'.pub\nHello', u'Hello')
        self.assertIsNotNone(page.published_at)
        self.assertIsNone(page.published_to)
        self.assertEqual(1, len(WikiPage.get_posts_of(None)))

    def test_second_publish(self):
        page1 = self.update_page(u'.pub\nHello 1')
        page2 = self.update_page(u'.pub\nHello 2')
        posts = WikiPage.get_posts_of(None)
        self.assertEqual(2, len(posts))
        self.assertEqual(page2.title, posts[1].newer_title)
        self.assertEqual(page1.title, posts[0].older_title)


class DefaultBlogUnpublishTest(AppEngineTestCase):
    def setUp(self):
        super(DefaultBlogUnpublishTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

        self.update_page(u'.pub\nHello 1', u'Hello 1')
        self.update_page(u'.pub\nHello 2', u'Hello 2')
        self.update_page(u'.pub\nHello 3', u'Hello 3')

    def test_unpublish_middle(self):
        self.update_page(u'Hello 2', u'Hello 2')

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)

    def test_unpublish_oldest(self):
        self.update_page(u'Hello 1', u'Hello 1')

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 2', newer.older_title)

    def test_unpublish_newest(self):
        self.update_page(u'Hello 3', u'Hello 3')

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 2', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)

    def test_delete_published_page(self):
        self.login('a@x.com', 'a', is_admin=True)
        WikiPage.get_by_title(u'Hello 2').delete(self.get_cur_user())

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)


class CustomBlogTest(AppEngineTestCase):
    def setUp(self):
        super(CustomBlogTest, self).setUp()
        self.login('ak@gmail.com', 'ak')

    def test_publish(self):
        page = self.update_page(u'.pub Posts\nHello')
        self.assertIsNotNone(page.published_at)
        self.assertEqual('Posts', page.published_to)
        self.assertEqual(1, len(WikiPage.get_posts_of('Posts')))

    def test_specify_page_to_published_page(self):
        # .pub -> .pub BBS
        self.update_page(u'.pub\nHello', u'Hello')
        page = self.update_page(u'.pub BBS\nHello', u'Hello')

        self.assertIsNotNone(page.published_at)
        self.assertEqual('BBS', page.published_to)

    def test_change_page_of_published_page(self):
        # .pub BBS1 -> .pub BBS2
        self.update_page(u'.pub BBS1\nHello', u'Hello')
        page = self.update_page(u'.pub BBS2\nHello', u'Hello')
        self.assertIsNotNone(page.published_at)
        self.assertEqual('BBS2', page.published_to)

    def test_remove_page_of_published_page(self):
        # .pub BBS -> .pub
        self.update_page(u'.pub BBS\nHello', u'Hello')
        page = self.update_page(u'.pub\nHello', u'Hello')
        self.assertIsNotNone(page.published_at)
        self.assertEqual(None, page.published_to)

    def test_unpublish_published_page(self):
        # .pub BBS -> (null)
        self.update_page(u'.pub BBS\nHello', u'Hello')
        page = self.update_page(u'Hello', u'Hello')
        self.assertIsNone(page.published_at)
        self.assertEqual(None, page.published_to)

    def test_multiple_custom_blogs(self):
        self.update_page(u'.pub B1', u'b1p1')
        self.update_page(u'.pub B1', u'b1p2')
        self.update_page(u'.pub B2', u'b2p1')
        self.update_page(u'.pub B2', u'b2p2')

        b1p1 = WikiPage.get_by_title(u'b1p1')
        b1p2 = WikiPage.get_by_title(u'b1p2')
        b2p1 = WikiPage.get_by_title(u'b2p1')
        b2p2 = WikiPage.get_by_title(u'b2p2')
        self.assertEqual('b1p2', b1p1.newer_title)
        self.assertEqual('b1p1', b1p2.older_title)
        self.assertEqual('b2p2', b2p1.newer_title)
        self.assertEqual('b2p1', b2p2.older_title)
