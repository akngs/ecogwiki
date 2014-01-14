# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


RE_PARTIALS = ur'\[(?P<check>\s|x)\]'


class PartialsExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        pattern = Partials(RE_PARTIALS)
        md.inlinePatterns.add('partials', pattern, "<wikilink")


class Partials(Pattern):
    def handleMatch(self, m):
        el = etree.Element('input')
        el.set('type', 'checkbox')
        if m.group('check') == 'x':
            el.set('checked', 'checked')
        return el
