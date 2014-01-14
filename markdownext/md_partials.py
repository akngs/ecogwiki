# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


RE_PARTIALS = ur'(' \
              ur'(\[(?P<check>\s|x)])' \
              ur'|' \
              ur'(\[(?P<log>__)])' \
              ur')'


class PartialsExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        pattern = Partials(RE_PARTIALS)
        md.inlinePatterns.add('partials', pattern, "<wikilink")


class Partials(Pattern):
    def handleMatch(self, m):
        if m.group('check'):
            el = etree.Element('input')
            el.set('type', 'checkbox')
            el.set('class', 'partial checkbox')
            if m.group('check') == 'x':
                el.set('checked', 'checked')
            return el
        elif m.group('log'):
            form = etree.Element('form')
            form.set('class', 'partial log')
            field = etree.SubElement(form, 'input')
            field.set('type', 'text')
            submit = etree.SubElement(form, 'input')
            submit.set('type', 'submit')
            submit.set('value', 'Update')
            return form
        else:
            return ''
