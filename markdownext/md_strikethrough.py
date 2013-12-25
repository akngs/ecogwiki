# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree

RE_STRIKE = ur'~~(?P<text>.+?)~~'


class StrikethroughExtension(Extension):
    def __init__(self):
        super(StrikethroughExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        pattern = Strikethrough(RE_STRIKE)
        pattern.md = md
        md.inlinePatterns.add('strikethrough', pattern, "<link")


class Strikethrough(Pattern):
    def __init__(self, pattern):
        super(Strikethrough, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        el = etree.Element('strike')
        el.text = m.group('text')
        return el
