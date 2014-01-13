# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


url_re = r'(' \
         r'(?P<plainurl>((?P<itemprop>[^\s\:]+)\:\:)?(?P<url>\w+://' \
         r'[a-zA-Z0-9\~\!\@\#\$\%\^\&\*\-\_\=\+\[\]\\\:\;\"\'\,\.\'' \
         r'\?/]' \
         r'+))' \
         r'|' \
         r'(?P<email>[^\s]+@[^\s]+\.' \
         r'[a-zA-Z0-9\~\!\@\#\$\%\^\&\*\-\_\=\+\[\]\\\:\;\"\'\,\.\'/]' \
         r'{2,3})' \
         r')'


class URLExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        url_pattern = UrlPattern(url_re)
        md.inlinePatterns.add('url', url_pattern, "<backtick")
        del md.inlinePatterns['emphasis2']


class UrlPattern(Pattern):
    def handleMatch(self, m):
        if m.group('plainurl'):
            url = m.group('url')
            a = etree.Element('a')
            a.text = url
            a.set('href', url)
            a.set('class', 'plainurl')
            if m.group('itemprop'):
                a.set('itemprop', m.group('itemprop'))
            return a
        else:
            url = m.group('email')
            a = etree.Element('a')
            a.text = url
            a.set('href', 'mailto:%s' % url)
            a.set('class', 'email')
            return a
