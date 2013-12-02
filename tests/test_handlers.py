# -*- coding: utf-8 -*-
import re
import os
import json
import main
import webapp2
import unittest
import lxml.etree
from models import WikiPage
import xml.etree.ElementTree as ET
from google.appengine.ext import testbed
from lxml.html import html5parser, tostring


class ContentTypeTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        self.testbed.init_taskqueue_stub()

        self.browser = Browser()

    def tearDown(self):
        self.testbed.deactivate()
        self.browser.logout()

    def test_get_default_content_type(self):
        p = WikiPage.get_by_title(u'Test')
        p.update_content(u'Hello', 0, '')
        self.browser.get('/Test')
        self.assertEqual('text/html; charset=utf-8', self.browser.res.headers['Content-type'])

    def test_get_custom_content_type(self):
        p = WikiPage.get_by_title(u'Test')
        p.update_content(u'.content-type text/plain\nHello', 0, '')
        self.browser.get('/Test')
        self.assertEqual('text/plain; charset=utf-8', self.browser.res.headers['Content-type'])
        self.assertEqual('Hello', self.browser.res.body)

    def test_get_custom_content_type_with_type_param(self):
        p = WikiPage.get_by_title(u'Test')
        p.update_content(u'.content-type text/plain\nHello', 0, '')
        self.browser.get('/Test?_type=form')
        self.assertEqual('text/html; charset=utf-8', self.browser.res.headers['Content-type'])

    def test_should_not_restrict_read_access_to_custom_content_type(self):
        p = WikiPage.get_by_title(u'Test')
        self.assertRaises(ValueError, p.update_content, u'.read blah\n.content-type text/plain\nHello', 0, '')


class WikiPageHandlerTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        self.testbed.init_taskqueue_stub()

        self.fixtures = [
            [u'Home', u'Home'],
            [u'A', u'Goto [[Home]]'],
            [u'Post A', u'.pub\nHello'],
            [u'Post B', u'.pub\nHello'],
            [u'Post C', u'.pub BBS\nHello'],
            [u'BBS', u'.schema Blog\nBlog'],
        ]

        for title, body in self.fixtures:
            page = WikiPage.get_by_title(title)
            page.update_content(body, 0, None)

        self.browser = Browser()

    def tearDown(self):
        self.testbed.deactivate()
        self.browser.logout()

    def test_get_sp_chages(self):
        for _ in range(2):
            self.browser.get('/sp.changes')
            links = self.browser.query('.//table//a')
            link_texts = [link.text for link in links]
            self.assertEqual([u'BBS', u'Post C', u'Post B', u'Post A', u'A', u'Home'], link_texts)

    def test_get_sp_index(self):
        for _ in range(2):
            self.browser.get('/sp.index')
            links = self.browser.query('.//table//a')
            link_texts = [link.text for link in links]
            self.assertEqual([u'A', u'BBS', u'Home', u'Post A', u'Post B', u'Post C'], link_texts)

    def test_get_sp_posts(self):
        for _ in range(2):
            self.browser.get('/sp.posts')
            links = self.browser.query('.//table//a')
            link_texts = [link.text for link in links]
            self.assertEqual([u'Post B', u'Post A'], link_texts)

    def test_get_posts_to_page(self):
        for _ in range(2):
            self.browser.get('/BBS')
            links = self.browser.query('.//table//a')
            link_texts = [link.text for link in links]
            self.assertEqual([u'Post C'], link_texts)

    def test_get_wikipage(self):
        for _ in range(2):
            self.browser.get('/A')
            links = self.browser.query('.//article//a[@class=\'wikipage\']')
            link_texts = [link.text for link in links]
            self.assertEqual(['Home'], link_texts)

    def test_post_new_page(self):
        self.browser.login('ak@gmailcom', 'ak')
        self.browser.post('/New_page', 'body=[[Link!]]&revision=0&comment=&preview=0')

        for _ in range(2):
            self.browser.get('/New_page')
            links = self.browser.query('.//article//a[@class=\'wikipage\']')
            link_texts = [link.text for link in links]
            self.assertEqual([u'Link!'], link_texts)

    def test_post_updated_page(self):
        self.browser.login('ak@gmailcom', 'ak')
        self.browser.post('/New_page', 'body=[[Link!]]&revision=0&comment=&preview=0')
        self.browser.post('/New_page', 'body=[[Link!!]]&revision=1&comment=&preview=0')

        for _ in range(2):
            self.browser.get('/New_page')
            links = self.browser.query('.//article//a[@class=\'wikipage\']')
            link_texts = [link.text for link in links]
            self.assertEqual([u'Link!!'], link_texts)

    def test_post_new_page_should_fail_if_user_is_none(self):
        self.browser.post('/New_page', 'body=[[Link!]]&revision=0&comment=&preview=0')
        self.assertEqual(403, self.browser.res.status_code)

    def test_new_page_should_be_shown_in_sp_changes(self):
        self.browser.login('ak@gmailcom', 'ak')
        self.browser.post('/New_page', 'body=[[Link!]]&revision=0&comment=&preview=0')

        for _ in range(2):
            self.browser.get('/sp.changes')
            links = self.browser.query('.//table//a')
            link_texts = [link.text for link in links]
            self.assertEqual([u'New page', u'BBS', u'Post C', u'Post B', u'Post A', u'A', u'Home'],
                             link_texts)

    def test_new_page_should_be_shown_in_sp_index(self):
        self.browser.login('ak@gmailcom', 'ak')
        self.browser.post('/New_page', 'body=[[Link!]]&revision=0&comment=&preview=0')

        for _ in range(2):
            self.browser.get('/sp.index')
            links = self.browser.query('.//table//a')
            link_texts = [link.text for link in links]
            self.assertEqual([u'A', u'BBS', u'Home', u'New page', u'Post A', u'Post B', u'Post C'],
                             link_texts)

    def test_redirect_metadata(self):
        page = WikiPage.get_by_title(u'Hi')
        page.update_content(u'.redirect Hello World', 0, '')

        self.browser.get('/Hi')
        self.assertEqual(303, self.browser.res.status_code)
        self.assertEqual('http://localhost/Hello_World',
                         self.browser.res.location)


class RevisionTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        self.testbed.init_taskqueue_stub()
        self.parser = html5parser.HTMLParser(strict=True)
        self.browser = Browser()

    def test_rev(self):
        page = WikiPage.get_by_title(u'A')
        page.update_content(u'Hello', 0, '')
        page.update_content(u'Hello there', 1, '')

        self.browser.get('/A?rev=1')
        self.assertEqual(200, self.browser.res.status_code)

        self.browser.get('/A?_type=rawbody&rev=1')
        self.assertEqual(200, self.browser.res.status_code)

        self.browser.get('/A?_type=body&rev=1')
        self.assertEqual(200, self.browser.res.status_code)

    def test_rev_param(self):
        page = WikiPage.get_by_title(u'A')
        page.update_content(u'Hello', 0, '')
        page.update_content(u'Hello there', 1, '')

        self.browser.get('/A?_type=rawbody&rev=1')
        self.assertEqual(u'Hello', self.browser.res.body)

        self.browser.get('/A?_type=rawbody&rev=2')
        self.assertEqual(u'Hello there', self.browser.res.body)

        self.browser.get('/A?_type=rawbody&rev=latest')
        self.assertEqual(u'Hello there', self.browser.res.body)

    def test_rev_acl(self):
        self.browser.login('a@x.com', 'a')
        page = WikiPage.get_by_title(u'A')
        page.update_content(u'Hello', 0, '')
        page.update_content(u'.read a@x.com\nHello there', 1, '')

        self.browser.get('/A?_type=rawbody&rev=1')
        self.assertEqual(200, self.browser.res.status_code)
        self.browser.get('/A?_type=rawbody&rev=2')
        self.assertEqual(200, self.browser.res.status_code)

        self.browser.logout()
        self.browser.get('/A?_type=rawbody&rev=1')
        self.assertEqual(200, self.browser.res.status_code)
        self.browser.get('/A?_type=rawbody&rev=2')
        self.assertEqual(403, self.browser.res.status_code)


class HTML5ValidationTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        self.testbed.init_taskqueue_stub()
        self.parser = html5parser.HTMLParser(strict=True)
        self.browser = Browser()

        self.fixtures = [
            [u'Home', u'Goto [[한글 제목]]'],
            [u'A', u'Goto [[Home]]'],
            [u'한글 제목', u'Goto [[Home]]'],
            [u'Presentation', u'.pt\nHello'],
            [u'Blog post', u'.pub\nHello'],
        ]

        for title, body in self.fixtures:
            page = WikiPage.get_by_title(title)
            page.update_content(body, 0, None)
            # update again to create revisions
            page.update_content(body + u'!', 1, None)

    def tearDown(self):
        self.testbed.deactivate()
        self.browser.logout()

    def test_normal_pages(self):
        for title, _ in self.fixtures:
            self._validate('/%s' % WikiPage.title_to_path(title),
                           'html')
            self._validate('/%s?rev=1' % WikiPage.title_to_path(title),
                           'html')
            self._validate('/%s?_type=body' % WikiPage.title_to_path(title),
                           'html')
            self._validate('/%s?_type=form' % WikiPage.title_to_path(title),
                           'html')

    def test_special_pages(self):
        def validate():
            self._validate('/sp.changes', 'html')
            self._validate('/sp.changes?_type=atom', 'xml')

            self._validate('/sp.index', 'html')
            self._validate('/sp.index?_type=atom', 'xml')

            self._validate('/sp.search?_type=json&format=opensearch', 'json')

            self._validate('/="Home"', 'html')
            self._validate('/="Home"?_type=body', 'html')
            self._validate('/="Home"?_type=json', 'json')

            self._validate('/sp.titles?_type=json', 'json')

            self._validate('/sp.posts', 'html')
            self._validate('/sp.posts?_type=atom', 'xml')

            self._validate('/sp.randomly_update_related_pages', 'text')
            self._validate('/sp.randomly_update_related_pages?recent=1', 'text')

        self.browser.login('user@example.com', 'ak', is_admin=False)
        validate()
        self._validate('/sp.preferences', 'html', 200)

        self.browser.login('user@example.com', 'ak', is_admin=True)
        validate()
        self._validate('/sp.preferences', 'html', 200)

        self.browser.logout()
        validate()
        self._validate('/sp.preferences', 'html', 403)

    def _validate(self, url, validator, status_code=200):
        req = webapp2.Request.blank(url)
        res = req.get_response(main.app)

        self.assertEqual(status_code, res.status_code)

        if validator == 'html':
            self.assertEqual('text/html', res.content_type)
            html5parser.fromstring(res.body, parser=self.parser)
        elif validator == 'xml':
            self.assertEqual('text/xml', res.content_type)
            lxml.etree.XML(res.body)
        elif validator == 'json':
            self.assertEqual('application/json', res.content_type)
            json.loads(res.body)
        elif validator == 'text':
            self.assertEqual('text/plain', res.content_type)


class Browser(object):
    def __init__(self):
        self.parser = html5parser.HTMLParser(strict=True)
        self.res = None

    def get(self, url):
        req = webapp2.Request.blank(url)
        self.res = req.get_response(main.app)

    def post(self, url, content):
        req = webapp2.Request.blank(url)
        req.method = 'POST'
        req.body = content
        self.res = req.get_response(main.app)

    def query(self, path):
        html = self.res.body
        p = html5parser.fromstring(html, parser=self.parser)
        xml = ET.fromstring(tostring(p))
        path = re.sub(r'/(\w+\d?)', r'/{http://www.w3.org/1999/xhtml}\1', path)
        return xml.findall(path)

    def login(self, email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    def logout(self):
        self.login(None, None)
