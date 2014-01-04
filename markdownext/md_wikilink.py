# -*- coding: utf-8 -*-
import re
import urllib2
from markdown.util import etree
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern


RE_WIKILINK = ur'\[\[' \
              ur'((?P<rel>[^\]=]+?)\:\:)?' \
              ur'(' \
              ur'(?P<date>(?P<y>\d+)(-(?P<m>(0[1-9]|1[0-2]|\?\?))-(?P<d>(0[1-9]|[12][0-9]|3[01]|\?\?)))?( (?P<bce>BCE))?)|' \
              ur'(?P<plain>.+?)' \
              ur')\]\]'


class WikiLinkExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        wikilink_pattern = WikiLinks(RE_WIKILINK)
        md.inlinePatterns.add('wikilink', wikilink_pattern, "<link")


class WikiLinks(Pattern):
    def handleMatch(self, m):
        return _render_match(m)


def render_wikilink(linktext):
    m = re.match(RE_WIKILINK, u'[[%s]]' % linktext)
    return etree.tostring(_render_match(m))


def _build_url(label):
    return '/%s' % urllib2.quote(label.replace(' ', '_').encode('utf-8'))


def _render_link(text, classname):
    url = _build_url(text)
    a = etree.Element('a')
    a.text = text
    a.set('href', url)
    a.set('class', classname)
    return a


def _render_match(m):
    if m.group('plain'):
        text = m.group('plain')
        if text[0] == '=':
            a = _render_link(text, 'wikiquery')
        else:
            a = _render_link(text, 'wikipage')
            if m.group('rel'):
                a.set('itemprop', m.group('rel'))
    elif m.group('date'):
        links = date_links(m)

        # handle year
        year = links[0]
        a = etree.Element('time')
        a.set('datetime', m.group('date'))
        year_a = etree.SubElement(a, 'a')
        year_a.text = year[0]
        year_a.set('href', _build_url(year[1]))
        year_a.set('class', 'wikipage')

        if m.group('m') or m.group('d'):
            hyphen = etree.SubElement(a, 'span')
            hyphen.text = '-'

            # handle month and date
            if len(links) > 1:
                date = links[1]
                rest_a = etree.SubElement(a, 'a')
                rest_a.text = date[0]
                rest_a.set('href', _build_url(date[1]))
                rest_a.set('class', 'wikipage')
            else:
                unknown_date = etree.SubElement(a, 'span')
                unknown_date.text = '??-??'

        # handle BCE
        if year[2]:
            bce = etree.SubElement(a, 'span')
            bce.text = ' BCE'

        if m.group('rel'):
            a.set('itemprop', m.group('rel'))
    else:
        a = ''

    return a


def parse_wikilinks(itemtype, text):
    wikilinks = {}
    for m in re.finditer(RE_WIKILINK, text):
        if m.group('plain') and m.group('plain')[0] == '=':
            # skip wikiquery
            continue

        rel_type = m.group('rel') if m.group('rel') else u'relatedTo'
        rel = u'%s/%s' % (itemtype, rel_type)

        if rel not in wikilinks:
            wikilinks[rel] = []

        if m.group('plain'):
            wikilinks[rel].append(m.group('plain'))
        else:
            # m.group('date'):
            links = date_links(m)
            for link in links:
                wikilinks[rel].append(link[1])

    return wikilinks


def date_links(m):
    wikilinks = []

    year = m.group('y')
    month = m.group('m')
    date = m.group('d')
    bce = m.group('bce') == 'BCE'
    bce_str = ' BCE' if bce else ''

    # handle year
    wikilinks.append(('%s' % year, '%s%s' % (year, bce_str), bce))

    if month == '??' and date == '??':
        return wikilinks
    if month is None and date is None:
        return wikilinks

    # handle month and date
    month_num = int(month)
    month_name = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November',
                  'December'][month_num - 1]
    if date == u'??':
        wikilinks.append((u'%s-%s' % (month, date),
                          u'%s' % month_name))
    else:
        date_num = int(date)
        wikilinks.append((u'%s-%s' % (month, date),
                          u'%s %d' % (month_name, date_num)))

    return wikilinks
