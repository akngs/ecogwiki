# coding=utf-8
import os
import re
import main
import json
import jinja2
from pyatom import AtomFeed
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
    if value is None:
        return ''
    else:
        return value.strftime(pattern)


def userpage_link(user):
    if user is None:
        return '<span class="user">Anonymous</span>'
    else:
        preferences = UserPreferences.get_by_user(user)

        if preferences is None:
            return '<span class="user email">%s</span>' % user.email()
        elif preferences.userpage_title is None or len(preferences.userpage_title.strip()) == 0:
            return '<span class="user email">%s</span>' % user.email()
        else:
            path = to_abs_path(preferences.userpage_title)
            return '<a href="%s" class="user userpage wikilink">%s</a>' % (path, preferences.userpage_title)


def has_supported_language(hashbangs):
    config = WikiPage.get_config()
    return any(x in config['highlight']['supported_languages'] for x in hashbangs)


JINJA.filters['dt'] = format_datetime
JINJA.filters['sdt'] = format_short_datetime
JINJA.filters['isodt'] = format_iso_datetime
JINJA.filters['to_abs_path'] = to_abs_path
JINJA.filters['to_rel_path'] = to_rel_path
JINJA.filters['to_pluspath'] = to_pluspath
JINJA.filters['userpage'] = userpage_link
JINJA.filters['has_supported_language'] = has_supported_language


def render_posts_atom(req, title, pages):
    host = req.host_url
    config = WikiPage.get_config()
    if title is None:
        feed_title = '%s: posts' % config['service']['title']
        url = "%s/sp.posts?_type=atom" % host
    else:
        feed_title = title
        url = "%s/%s?_type=atom" % (WikiPage.title_to_path(title), host)

    feed = AtomFeed(title=feed_title,
                    feed_url=url,
                    url="%s/" % host,
                    author=config['admin']['email'])
    for page in pages:
        feed.add(title=page.title,
                 content_type="html",
                 content=page.rendered_body,
                 author=page.modifier,
                 url='%s%s' % (host, page.absolute_url),
                 updated=page.published_at)
    return feed.to_string()


def get_restype(req, default):
    return str(req.GET.get('_type', default))


def set_response_body(res, resbody, head):
    if head:
        res.headers['Content-Length'] = str(len(resbody))
    else:
        res.write(resbody)


def template(req, path, data):
    t = JINJA.get_template('templates/%s' % path)
    config = WikiPage.get_config()

    user = get_cur_user()
    preferences = None
    if user is not None:
        preferences = UserPreferences.get_by_user(user)

    data['is_local'] = req.host_url.startswith('http://localhost')
    data['is_mobile'] = is_mobile(req)
    data['user'] = user
    data['preferences'] = preferences
    data['users'] = users
    data['cur_url'] = req.url
    data['config'] = config
    data['app'] = {
        'version': main.VERSION,
    }
    return t.render(data)


def is_mobile(req):
    p = r'.*(Android|Fennec|GoBrowser|iPad|iPhone|iPod|Mobile|Opera Mini|Opera Mobi|Windows CE).*'
    if 'User-Agent' not in req.headers:
        return False
    return re.match(p, req.headers['User-Agent']) is not None


def obj_to_html(o, key=None):
    obj_type = type(o)
    if isinstance(o, dict):
        return render_dict(o)
    elif obj_type == list:
        return render_list(o)
    elif obj_type == str or obj_type == unicode:
        if key is not None and key == 'schema':
            return o
        else:
            return '<a href="%s">%s</a>' % (to_abs_path(o), o)
    else:
        return str(o)


def render_dict(o):
    if len(o) == 1:
        return obj_to_html(o.values()[0])
    else:
        html = ['<dl class="wq wq-dict">']
        for key, value in o.items():
            html.append('<dt class="wq-key-%s">' % key)
            html.append(key)
            html.append('</dt>')
            html.append('<dd class="wq-value-%s">' % key)
            html.append(obj_to_html(value, key))
            html.append('</dd>')
        html.append('</dl>')

        return '\n'.join(html)


def render_list(o):
    html = ['<ul class="wq wq-list">']
    for value in o:
        html.append('<li>')
        html.append(obj_to_html(value))
        html.append('</li>')
    html.append('</ul>')

    return '\n'.join(html)
