# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


RE_CHECKBOX = ur'\[(?P<check>\s|x)\]'


class CheckboxExtension(Extension):
    def __init__(self):
        super(CheckboxExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        pattern = Checkbox(RE_CHECKBOX)
        pattern.md = md
        md.inlinePatterns.add('checkbox', pattern, "<wikilink")


class Checkbox(Pattern):
    def __init__(self, pattern):
        super(Checkbox, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        el = etree.Element('input')
        el.set('type', 'checkbox')
        if m.group('check') == 'x':
            el.set('checked', 'checked')
        return el
