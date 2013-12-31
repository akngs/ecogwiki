# coding=utf-8
import os
import re
import main
import json
import jinja2
from google.appengine.api import users
from models import WikiPage, UserPreferences, get_cur_user


class Representation(object):
    def __init__(self, content, content_type):
        self._content = content
        self._content_type = content_type

    def respond(self, httpres, head):
        self._respond(httpres, head, self._content_type, self._content)

    def _respond(self, httpres, head, content_type, content):
        httpres.headers['Content-Type'] = content_type
        if head:
            httpres.headers['Content-Length'] = str(len(content))
        else:
            httpres.write(content)


class TemplateRepresentation(Representation):
    def __init__(self, content, httpreq, template_path):
        if template_path.endswith('.html'):
            content_type = 'text/html; charset=utf-8'
        elif template_path.endswith('.xml'):
            content_type = 'text/xml; charset=utf-8'
        else:
            content_type = 'text/plain; charset=utf-8'

        super(TemplateRepresentation, self).__init__(content, content_type)
        self._httpreq = httpreq
        self._template_path = template_path

    def respond(self, httpres, head):
        html = template(self._httpreq, self._template_path, self._content)
        self._respond(httpres, head, self._content_type, html)


class JsonRepresentation(Representation):
    def __init__(self, content):
        super(JsonRepresentation, self).__init__(content, 'application/json; charset=utf-8')

    def respond(self, httpres, head):
        self._respond(httpres, head, self._content_type, json.dumps(self._content))


class EmptyRepresentation(Representation):
    def __init__(self, rescode):
        super(EmptyRepresentation, self).__init__(None, None)
        self._rescode = rescode

    def respond(self, httpres, head):
        httpres.status = 400


JINJA = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


to_rel_path = lambda title: WikiPage.title_to_path(title)
to_abs_path = lambda title: '/' + to_rel_path(title)
to_pluspath = lambda title: '/%2B' + to_rel_path(title)
format_short_datetime = lambda v: _format_datetime(v, '%m-%d %H:%M')
format_datetime = lambda v: _format_datetime(v, '%Y-%m-%d %H:%M:%S')
format_iso_datetime = lambda v: _format_datetime(v, '%Y-%m-%dT%H:%M:%SZ')


def _format_datetime(value, pattern):
    return '' if value is None else value.strftime(pattern)


def userpage_link(user):
    if user is None:
        return '<span class="user">Anonymous</span>'

    preferences = UserPreferences.get_by_user(user)
    if preferences is None:
        return '<span class="user email">%s</span>' % user.email()
    elif preferences.userpage_title is None or len(preferences.userpage_title.strip()) == 0:
        return '<span class="user email">%s</span>' % user.email()
    path = to_abs_path(preferences.userpage_title)
    return '<a href="%s" class="user userpage wikilink">%s</a>' % (path, preferences.userpage_title)


def has_supported_language(hashbangs):
    langs = WikiPage.get_config()['highlight']['supported_languages']
    return any(lang in langs for lang in hashbangs)


JINJA.filters['dt'] = format_datetime
JINJA.filters['sdt'] = format_short_datetime
JINJA.filters['isodt'] = format_iso_datetime
JINJA.filters['to_abs_path'] = to_abs_path
JINJA.filters['to_rel_path'] = to_rel_path
JINJA.filters['to_pluspath'] = to_pluspath
JINJA.filters['userpage'] = userpage_link
JINJA.filters['has_supported_language'] = has_supported_language


def template(req, path, data):
    config = WikiPage.get_config()
    user = get_cur_user()
    data['is_local'] = req.host_url.startswith('http://localhost')
    data['is_mobile'] = is_mobile(req)
    data['user'] = user
    data['preferences'] = UserPreferences.get_by_user(user) if user is not None else None
    data['users'] = users
    data['cur_url'] = req.url
    data['config'] = config
    data['app'] = {'version': main.VERSION}
    return JINJA.get_template('templates/%s' % path).render(data)


def is_mobile(req):
    p = r'.*(Android|Fennec|GoBrowser|iPad|iPhone|iPod|Mobile|Opera Mini|Opera Mobi|Windows CE).*'
    if 'User-Agent' not in req.headers:
        return False
    return re.match(p, req.headers['User-Agent']) is not None
