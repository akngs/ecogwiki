from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


RE_ITEMPROP = ur'\{\{(' \
              ur'(?P<isbn>isbn\:\:(?P<isbnnum>[\dxX]{10,13}))|' \
              ur'((?P<key>[^\}]+?)\:\:(?P<value>[^\}]+?))' \
              ur')\}\}'


class ItemPropExtension(Extension):
    def __init__(self):
        super(ItemPropExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        item_prop_pattern = ItemProp(RE_ITEMPROP)
        item_prop_pattern.md = md
        md.inlinePatterns.add('itemprop', item_prop_pattern, "<link")


class ItemProp(Pattern):
    def __init__(self, pattern):
        super(ItemProp, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        if m.group('isbn'):
            num = m.group('isbnnum')
            el = etree.Element('a')
            el.text = num
            if num[:2] == '89':
                el.set('href', u'http://www.aladin.co.kr/shop/wproduct.aspx'
                               u'?ISBN=%s' % num)
            else:
                el.set('href', u'http://www.amazon.com/gp/product/%s' % num)
            el.set('class', 'isbn')
            el.set('itemprop', 'isbn')
        else:
            key = m.group('key')
            value = m.group('value')
            el = etree.Element('span')
            if key[0] == '.':
                el.set('class', key[1:])
            else:
                el.set('itemprop', key)
            el.text = value

        return el
