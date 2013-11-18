from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern


RE_MATHJAX = ur'((?P<inline>\\\((?P<tinline>.+?)\\\))|(?P<block>\$\$(?P<tblock>.+?)\$\$))'


class MathJaxExtension(Extension):
    def __init__(self):
        super(MathJaxExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        mathjax_pattern = MathJax(RE_MATHJAX)
        mathjax_pattern.md = md
        md.inlinePatterns.add('mathjax', mathjax_pattern, "<escape")


class MathJax(Pattern):
    def __init__(self, pattern):
        super(MathJax, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        if m.group('inline'):
            a = u'\\(%s\\)' % m.group('tinline')
        elif m.group('block'):
            a = u'$$%s$$' % m.group('tblock')
        else:
            a = ''

        return a
