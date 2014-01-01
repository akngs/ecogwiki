# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


RE_ITEMPROP = ur'\{\{(' \
              ur'(?P<isbn>isbn\:\:(?P<isbnnum>[\dxX]{10,13}))|' \
              ur'((?P<key>[^\}]+?)\:\:(?P<value>[^\}]+?))' \
              ur')\}\}'


class ItemPropExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        item_prop_pattern = ItemProp(RE_ITEMPROP)
        md.inlinePatterns.add('itemprop', item_prop_pattern, "<link")


class ItemProp(Pattern):
    def handleMatch(self, m):
        if m.group('isbn'):
            num = m.group('isbnnum')
            el = etree.Element('a')
            if num[:2] == '89':
                el.set('href', u'http://www.aladin.co.kr/shop/wproduct.aspx'
                               u'?ISBN=978%s' % num)
                el.text = '978%s' % num
            elif num[:5] == '97889':
                el.set('href', u'http://www.aladin.co.kr/shop/wproduct.aspx'
                               u'?ISBN=%s' % num)
                el.text = num
            else:
                el.set('href', u'http://www.amazon.com/gp/product/%s' % num)
                el.text = num
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
