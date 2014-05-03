# -*- coding: utf-8 -*-
import re
from markdown import Extension
from markdown.util import etree
from collections import OrderedDict
from markdown.preprocessors import Preprocessor


p = re.compile(
    r'('
    r'^(?P<youtube>https?\://www\.youtube\.com/watch\?v=(?P<youtube_vid>[^?]+))$'
    r'|'
    r'^(?P<youtube2><iframe.*?src="//www\.youtube\.com/embed/(?P<youtube2_vid>.+?)".*?>\s*</iframe>)$'
    r'|'
    r'^(?P<vimeo>https?\://vimeo\.com/(?P<vimeo_vid>\d+))$'
    r'|'
    r'^(?P<vimeo2><iframe.*?src="//player\.vimeo\.com/video/(?P<vimeo2_vid>\d+?)".*?>\s*</iframe>)$'
    r'|'
    r'^(?P<ted>https?\://www\.ted\.com/(?P<ted_vid>talks/.+\.html))$'
    r'|'
    r'^(?P<ted2><iframe.*?src="https?\://embed\.ted\.com/(?P<ted2_vid>talks/.+\.html)".*?>\s*</iframe>)$'
    r'|'
    r'^(?P<prezi>https?\://prezi\.com/(?P<prezi_vid>.+?)/.+?/#)$'
    r'|'
    r'^(?P<prezi2><iframe.*?src="https?\://prezi\.com/embed/(?P<prezi2_vid>.+?)/.+?".*?>\s*</iframe>)$'
    r'|'
    r'^(?P<slideshare><iframe.*?src="https?\://www\.slideshare\.net/slideshow/embed\_code/(?P<slideshare_vid>\d+?)".*?>\s*</iframe>\s*<div.+?</div>)$'
    r'|'
    r'^(?P<gcal><iframe.*?src="https?\://www\.google\.com/calendar/embed\?(?P<gcal_vid>.+?)".*?>\s*</iframe>)$'
    r'|'
    r'^(?P<googlemap>https?\://maps\.google\.com/(?P<googlemap_vid>.+?))$'
    r'|'
    r'^(?P<googlemap2>https?\://www\.google\.com/maps/(?P<googlemap2_vid>.+?))$'
    r'|'
    r'^(?P<googlemap3><iframe.*?src="https?\://maps\.google\.com/(?P<googlemap3_vid>.+?)".*?>\s*</iframe>)$'
    r'|'
    r'^(?P<navermap><table.*?td.*?><a href="(?P<navermap_url>http://map.naver.com.*?)"\s+.*><img src="(?P<navermap_imgsrc>http://.*?map.naver.com.*?)".*</a></td>.*</table>)$'
    r'|'
    r'^(?P<daummap><a href="(?P<daummap_url>http://map.daum.net.*?)"\s+.*<img.*src="(?P<daummap_imgsrc>http://map.*?.daum.net.*?)"\s+.*)$'
    r'|'
    r'^(?P<googless><iframe.*?src="https?\://docs.google.com/spreadsheets/(?P<googless_vid>.+?)".*?>\s*</iframe>)$'
    r')'
)


class EmbedPrepreprocessor(Preprocessor):
    def run(self, lines):
        for i, line in enumerate(lines):
            m = p.search(line.strip())
            if m:
                lines[i] = self.process(m)
        return lines

    def process(self, m):
        if m.group('youtube'):
            return self._create_video(m, 'youtube', 640, 390, 'http://www.youtube.com/embed/%s')
        elif m.group('youtube2'):
            return self._create_video(m, 'youtube2', 640, 390, 'http://www.youtube.com/embed/%s')
        elif m.group('vimeo'):
            return self._create_video(m, 'vimeo', 500, 281, 'http://player.vimeo.com/video/%s')
        elif m.group('vimeo2'):
            return self._create_video(m, 'vimeo2', 500, 281, 'http://player.vimeo.com/video/%s')
        elif m.group('ted'):
            return self._create_video(m, 'ted', 560, 315, 'http://embed.ted.com/%s')
        elif m.group('ted2'):
            return self._create_video(m, 'ted2', 560, 315, 'http://embed.ted.com/%s')
        elif m.group('prezi'):
            return self._create_video(m, 'prezi', 550, 400, 'http://prezi.com/embed/%s/?bgcolor=ffffff&lock_to_path=0&autoplay=0&autohide_ctrls=0&features=undefined&disabled_features=undefined')
        elif m.group('prezi2'):
            return self._create_video(m, 'prezi2', 550, 400, 'http://prezi.com/embed/%s/?bgcolor=ffffff&lock_to_path=0&autoplay=0&autohide_ctrls=0&features=undefined&disabled_features=undefined')
        elif m.group('slideshare'):
            return self._create_video(m, 'slideshare', 425, 355, 'http://www.slideshare.net/slideshow/embed_code/%s')
        elif m.group('gcal'):
            return self._create_video(m, 'gcal', 800, 600, 'http://www.google.com/calendar/embed?%s')
        elif m.group('googlemap'):
            return self._create_video(m, 'googlemap', 425, 350, 'http://maps.google.com/%s&output=embed')
        elif m.group('googlemap2'):
            return self._create_video(m, 'googlemap2', 425, 350, 'http://www.google.com/maps/%s&output=embed')
        elif m.group('googlemap3'):
            return self._create_video(m, 'googlemap3', 425, 350, 'http://maps.google.com/%s')
        elif m.group('googless'):
            return self._create_video(m, 'googless', 640, 480, 'http://docs.google.com/spreadsheets/%s')
        elif m.group('navermap'):
            return self._create_video_without_iframe(m, 'navermap', 460, 340)
        elif m.group('daummap'):
            return self._create_video_without_iframe(m, 'daummap', 500, 350)
        else:
            raise ValueError('Should not reach here')

    def _create_video_without_iframe(self, m, vtype, width, height):
        url = m.group('%s_url' % vtype)
        imgsrc = m.group('%s_imgsrc' % vtype)
        return "<div class=\"video %s\"><a href=\"%s\"><img src=\"%s\"></a></div>" % (vtype, url, imgsrc)

    def _create_video(self, m, vtype, width, height, url):
        vid = m.group('%s_vid' % vtype)
        url = url % vid
        url = url.replace('&amp;', '&')

        div = etree.Element('div')
        div.set('class', 'video %s' % vtype)
        iframe = etree.SubElement(div, 'iframe')
        iframe.set('allowfullscreen', 'true')
        iframe.set('frameborder', '0')
        iframe.set('width', str(width))
        iframe.set('height', str(height))
        iframe.set('scrolling', 'no')
        iframe.set('src', url)

        return etree.tostring(div)


class EmbedExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        preprocessors = md.preprocessors.items()
        preprocessors.insert(0, ('embed', EmbedPrepreprocessor(md.parser)))
        md.preprocessors = OrderedDict(preprocessors)
