# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern


RE_MATHJAX = ur'((?P<inline>\\\((?P<tinline>.+?)\\\))|(?P<block>\$\$(?P<tblock>.+?)\$\$))'


class MathJaxExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        mathjax_pattern = MathJax(RE_MATHJAX)
        md.inlinePatterns.add('mathjax', mathjax_pattern, "<escape")


class MathJax(Pattern):
    def handleMatch(self, m):
        if m.group('inline'):
            return u'\\(%s\\)' % m.group('tinline')
        else:
            return u'$$%s$$' % m.group('tblock')
