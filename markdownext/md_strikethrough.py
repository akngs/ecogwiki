# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree

RE_STRIKE = ur'~~(?P<text>.+?)~~'


class StrikethroughExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        pattern = Strikethrough(RE_STRIKE)
        md.inlinePatterns.add('strikethrough', pattern, "<link")


class Strikethrough(Pattern):
    def handleMatch(self, m):
        el = etree.Element('strike')
        el.text = m.group('text')
        return el
