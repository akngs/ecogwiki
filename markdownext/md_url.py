from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


class URLExtension(Extension):
    def __init__(self):
        super(URLExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md

        # append to end of inline patterns
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
        url_pattern = UrlPattern(url_re)
        url_pattern.md = md
        md.inlinePatterns.add('url', url_pattern, "<not_strong")


class UrlPattern(Pattern):
    def __init__(self, pattern):
        super(UrlPattern, self).__init__(pattern)

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
        elif m.group('email'):
            url = m.group('email')
            a = etree.Element('a')
            a.text = url
            a.set('href', 'mailto:%s' % url)
            a.set('class', 'email')
            return a
        else:
            raise Exception()
