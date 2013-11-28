# -*- coding: utf-8 -*-
import unittest
from models import WikiPage
from google.appengine.ext import testbed
from google.appengine.api import memcache


class WikiPageUpdateTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_rendered_body_should_be_cached(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0, '')
        self.assertIsNone(memcache.get(u'model\trendered_body\tHello'))

        _ = page.rendered_body
        self.assertIsNotNone(memcache.get(u'model\trendered_body\tHello'))

    def test_updating_should_invalidate_rendered_body_cache(self):
        memcache.set(u'model\trendered_body\tHello', u'value')

        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello 2', 0, '')

        self.assertIsNone(memcache.get(u'model\trendered_body\tHello'))

    def test_should_not_invalidate_cache_if_content_is_same(self):
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0, '')

        memcache.set(u'model\trendered_body\tHello', u'value')
        page.update_content(u'Hello', 0, '')

        self.assertIsNotNone(memcache.get(u'model\trendered_body\tHello'))

    def test_titles_cache(self):
        cache_key = u'model\ttitles\tNone'
        self.assertIsNone(memcache.get(cache_key))

        # populate cache
        WikiPage.get_titles(None)
        self.assertIsNotNone(memcache.get(cache_key))

        # invalidate cache by adding new page
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello', 0, '')
        self.assertIsNone(memcache.get(cache_key))

        # populate cache again
        WikiPage.get_titles(None)
        self.assertIsNotNone(memcache.get(cache_key))

        # Should not be invalidated because it's just an update
        page = WikiPage.get_by_title(u'Hello')
        page.update_content(u'Hello 2', 1, '')
        self.assertIsNotNone(memcache.get(cache_key))
