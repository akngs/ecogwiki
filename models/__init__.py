# -*- coding: utf-8 -*-

import markdown
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.attr_list import AttrListExtension
from markdownext import md_url, md_wikilink, md_itemprop, md_mathjax, md_strikethrough, md_tables

from google.appengine.api import users
from google.appengine.api import oauth

from utils import *
from toc_generator import TocGenerator
from conflict_error import ConflictError
from user_preferences import UserPreferences
from page_operation_mixin import PageOperationMixin
from wiki_page_revision import WikiPageRevision
from schema_data_index import SchemaDataIndex
from wiki_page import WikiPage


regions = {
    u'ㄱ': (u'가', u'나'),
    u'ㄴ': (u'나', u'다'),
    u'ㄷ': (u'다', u'라'),
    u'ㄹ': (u'라', u'마'),
    u'ㅁ': (u'마', u'바'),
    u'ㅂ': (u'바', u'사'),
    u'ㅅ': (u'사', u'아'),
    u'ㅇ': (u'아', u'자'),
    u'ㅈ': (u'자', u'차'),
    u'ㅊ': (u'차', u'카'),
    u'ㅋ': (u'카', u'타'),
    u'ㅌ': (u'타', u'파'),
    u'ㅍ': (u'파', u'하'),
    u'ㅎ': (u'하', u'힣'),
}


def title_grouper(title):
    title = title.upper()
    head = title[0]
    if 'A' <= head <= 'Z' or '0' <= head <= '9':
        return head

    for key, values in regions.items():
        if values[0] <= head < values[1]:
            return key

    return 'Misc'


def is_admin_user(user):
    if not user:
        return False

    if users.is_current_user_admin():
        return True

    try:
        if oauth.is_current_user_admin():
            return True
    except oauth.OAuthRequestError:
        pass

    return False


md = markdown.Markdown(
    extensions=[
        md_wikilink.WikiLinkExtension(),
        md_itemprop.ItemPropExtension(),
        md_url.URLExtension(),
        md_mathjax.MathJaxExtension(),
        md_strikethrough.StrikethroughExtension(),
        md_tables.TableExtension(),
        DefListExtension(),
        AttrListExtension(),
    ],
    safe_mode=False,
)

