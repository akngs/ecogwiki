# -*- coding: utf-8 -*-
from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


url_re = r'(' \
         r'(?P<youtube>https?\://www\.youtube\.com/watch\?v=(?P<youtube_vid>[^?]+))' \
         r'|' \
         r'(?P<vimeo>https?\://vimeo\.com/(?P<vimeo_vid>\d+))' \
         r'|' \
         r'(?P<ted>https?\://www\.ted\.com/(?P<ted_vid>talks/.+\.html))' \
         r'|' \
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
        md.inlinePatterns.add('url', url_pattern, "<not_strong")


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
        elif m.group('youtube'):
            return UrlPattern._create_video(m, 'youtube', 640, 390, 'http://www.youtube.com/embed/%s')
        elif m.group('vimeo'):
            return UrlPattern._create_video(m, 'vimeo', 500, 281, 'http://player.vimeo.com/video/%s')
        elif m.group('ted'):
            return UrlPattern._create_video(m, 'ted', 560, 315, 'http://embed.ted.com/%s')
        else:
            # m.group('email'):
            url = m.group('email')
            a = etree.Element('a')
            a.text = url
            a.set('href', 'mailto:%s' % url)
            a.set('class', 'email')
            return a

    @staticmethod
    def _create_video(m, vtype, width, height, url):
        vid = m.group('%s_vid' % vtype)
        div = etree.Element('div')
        div.set('class', 'video %s' % vtype)
        iframe = etree.SubElement(div, 'iframe')
        iframe.set('width', str(width))
        iframe.set('height', str(height))
        iframe.set('frameborder', '0')
        iframe.set('allowfullscreen', 'true')
        iframe.set('src', url % vid)
        return div
