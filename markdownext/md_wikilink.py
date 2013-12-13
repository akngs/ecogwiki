import re
import urllib2
from markdown.util import etree
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern

              # ur'(?P<date>(?P<y>\d+)-(?P<m>(0[1-9]|1[0-2]|\?\?))-(?P<d>([0-2][1-9]|3[0-1]|\?\?))' \

RE_WIKILINK = ur'\[\[' \
              ur'((?P<rel>[^\]=]+?)\:\:)?' \
              ur'(' \
              ur'(?P<date>(?P<y>\d+)-(?P<m>(0[1-9]|1[0-2]|\?\?))-(?P<d>(0[1-9]|[12][0-9]|3[01]|\?\?))' \
              ur'( (?P<bce>BCE))?)|' \
              ur'(?P<plain>.+?)' \
              ur')\]\]'


class WikiLinkExtension(Extension):
    def __init__(self):
        super(WikiLinkExtension, self).__init__()
        self.md = None

    def extendMarkdown(self, md, md_globals):
        self.md = md
        wikilink_pattern = WikiLinks(RE_WIKILINK)
        wikilink_pattern.md = md
        md.inlinePatterns.add('wikilink', wikilink_pattern, "<link")


class WikiLinks(Pattern):
    def __init__(self, pattern):
        super(WikiLinks, self).__init__(pattern)
        self.config = []

    def handleMatch(self, m):
        return _render_match(m)


def render_wikilink(linktext):
    m = re.match(RE_WIKILINK, u'[[%s]]' % linktext)
    return etree.tostring(_render_match(m))


def _build_url(label):
    return '/%s' % urllib2.quote(label.replace(' ', '_').encode('utf-8'))


def _render_match(m):
    if m.group('plain'):
        text = plain_link(m)
        if text[0] == '=':
            # treat it as a wikiquery link
            url = _build_url(text)
            a = etree.Element('a')
            a.text = text
            a.set('href', url)
            a.set('class', 'wikiquery')
        else:
            url = _build_url(text)
            a = etree.Element('a')
            a.text = text
            a.set('href', url)
            a.set('class', 'wikipage')

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

        if m.group('rel'):
            rel = u'%s/%s' % (itemtype, m.group('rel'))
        else:
            rel = u'%s/%s' % (itemtype, u'relatedTo')

        if rel not in wikilinks:
            wikilinks[rel] = []

        if m.group('plain'):
            wikilinks[rel].append(plain_link(m))
        elif m.group('date'):
            links = date_links(m)
            for link in links:
                wikilinks[rel].append(link[1])
        else:
            raise Exception('Should not reach here')

    return wikilinks


def plain_link(m):
    return m.group('plain')


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

    # handle month and date
    month_num = int(month, 10)
    month_name = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November',
                  'December'][month_num - 1]
    if date == u'??':
        wikilinks.append((u'%s-%s' % (month, date),
                          u'%s' % month_name))
    else:
        date_num = int(date, 10)
        wikilinks.append((u'%s-%s' % (month, date),
                          u'%s %d' % (month_name, date_num)))

    return wikilinks


KNOWN_RELS = {
    u'author': (u'Author of', u'Author'),
    u'birthDate': (u'Births', u'Birth date'),
    u'datePublished': (u'Publications', u'Published date'),
    u'deathDate': (u'Deaths', u'Deaths date'),
    u'programmingLanguage': (u'Codes', u'Programming language'),
    u'relatedTo': (u'Related to', u'Related to'),
}


def humane_rel(rel, inlink=True):
    if rel in KNOWN_RELS:
        labels = KNOWN_RELS[rel]
        if inlink:
            return labels[0]
        else:
            return labels[1]
    else:
        return rel
