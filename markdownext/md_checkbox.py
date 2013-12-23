from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree

RE_EMPTY = ur'\[ \]'
RE_CHECK = ur'\[x\]'

class EmptyCheckboxExtension(Extension):
    def __init__(self):
        super(EmptyCheckboxExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        pattern = EmptyCheckbox(RE_EMPTY)
        pattern.md = md
        md.inlinePatterns.add('empty_checkbox', pattern, "<wikilink")


class EmptyCheckbox(Pattern):
    def __init__(self, pattern):
        super(EmptyCheckbox, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        el = etree.Element('input')
        el.set('type', 'checkbox')
        return el

class CheckboxExtension(Extension):
    def __init__(self):
        super(CheckboxExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        pattern = Checkbox(RE_CHECK)
        pattern.md = md
        md.inlinePatterns.add('checkbox', pattern, "<wikilink")

class Checkbox(Pattern):
    def __init__(self, pattern):
        super(Checkbox, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        el = etree.Element('input')
        el.set('type', 'checkbox')
        el.set('checked', 'checked')
        return el