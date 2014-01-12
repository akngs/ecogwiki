# -*- coding: utf-8 -*-
import re
from markdown import Extension
from collections import OrderedDict
from markdown.preprocessors import Preprocessor


p = re.compile(
    r'('
    r'^(?P<youtube>https?\://www\.youtube\.com/watch\?v=(?P<youtube_vid>[^?]+))$'
    r'|'
    r'^(?P<youtube2><iframe.*?src="//www\.youtube\.com/embed/(?P<youtube2_vid>.+?)".*?></iframe>)$'
    r'|'
    r'^(?P<vimeo>https?\://vimeo\.com/(?P<vimeo_vid>\d+))$'
    r'|'
    r'^(?P<vimeo2><iframe.*?src="//player\.vimeo\.com/video/(?P<vimeo2_vid>\d+?)".*?></iframe>)$'
    r'|'
    r'^(?P<ted>https?\://www\.ted\.com/(?P<ted_vid>talks/.+\.html))$'
    r'|'
    r'^(?P<ted2><iframe.*?src="https?\://embed\.ted\.com/(?P<ted2_vid>talks/.+\.html)".*?></iframe>)$'
    r'|'
    r'^(?P<prezi>https?\://prezi\.com/(?P<prezi_vid>.+?)/.+?/#)$'
    r'|'
    r'^(?P<prezi2><iframe.*?src="https?\://prezi\.com/embed/(?P<prezi2_vid>.+?)/.+?".*?></iframe>)$'
    r')'
)

class EmbedPrepreprocessor(Preprocessor):
    def run(self, lines):
        for i, line in enumerate(lines):
            m = p.search(line)
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
        else:
            raise ValueError('Should not reach here')

    def _create_video(self, m, vtype, width, height, url):
        vid = m.group('%s_vid' % vtype)
        url = url % vid
        return u'<div class="video %s"><iframe allowfullscreen="true" frameborder="0" height="%d" src="%s" width="%d"></iframe></div>' % (vtype, height, url, width)


class EmbedExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        preprocessors = md.preprocessors.items()
        preprocessors.insert(0, ('embed', EmbedPrepreprocessor(md.parser)))
        md.preprocessors = OrderedDict(preprocessors)
