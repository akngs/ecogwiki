# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


RE_CHECKBOX = ur'\[(?P<check>\s|x)\]'


class CheckboxExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        pattern = Checkbox(RE_CHECKBOX)
        md.inlinePatterns.add('checkbox', pattern, "<wikilink")


class Checkbox(Pattern):
    def handleMatch(self, m):
        el = etree.Element('input')
        el.set('type', 'checkbox')
        if m.group('check') == 'x':
            el.set('checked', 'checked')
        return el
