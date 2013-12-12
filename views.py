# -*- coding: utf-8 -*-
import os
import re
import json
import main
import cache
import jinja2
import search
import urllib2
import webapp2
import operator
import logging
from pyatom import AtomFeed
from itertools import groupby
from collections import OrderedDict
from google.appengine.api import users
from google.appengine.api import oauth
from google.appengine.ext import deferred
from models import WikiPage, WikiPageRevision, UserPreferences, title_grouper, ConflictError

logger = logging.getLogger(__name__)

JINJA = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


def format_short_datetime(value):
    if value is None:
        return ''
    return value.strftime('%m-%d %H:%M')


def format_datetime(value):
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')


def format_iso_datetime(value):
    if value is None:
        return ''
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def to_path(title):
    return '/' + WikiPage.title_to_path(title)


def to_pluspath(title):
    return '/%2B' + WikiPage.title_to_path(title)


def urlencode(s):
    return urllib2.quote(s.encode('utf-8'))


def userpage_link(user):
    if user is None:
        return '<span class="user">Anonymous</span>'
    else:
        email = user.email()
        preferences = UserPreferences.get_by_email(email)

        if preferences is None:
            return '<span class="user email">%s</span>' % email
        elif preferences.userpage_title is None or len(preferences.userpage_title.strip()) == 0:
            return '<span class="user email">%s</span>' % email
        else:
            path = to_path(preferences.userpage_title)
            return '<a href="%s" class="user userpage wikilink">%s</a>' % (path, preferences.userpage_title)


def has_supported_language(hashbangs):
    config = WikiPage.get_config()
    return any(x in config['highlight']['supported_languages'] for x in hashbangs)


JINJA.filters['dt'] = format_datetime
JINJA.filters['sdt'] = format_short_datetime
JINJA.filters['isodt'] = format_iso_datetime
JINJA.filters['to_path'] = to_path
JINJA.filters['to_pluspath'] = to_pluspath
JINJA.filters['userpage'] = userpage_link
JINJA.filters['has_supported_language'] = has_supported_language


#
# Codes here are completely fucked up.
# Introduce "Resource" class to reduce duplications and conditionals.
#

class SearchHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        cache.create_prc()
        expression = WikiPage.path_to_title(path)
        parsed_expression = search.parse_expression(expression)
        scoretable = WikiPage.search(expression)

        positives = dict([(k, v) for k, v in scoretable.items() if v >= 0.0])
        positives = OrderedDict(sorted(positives.iteritems(),
                                       key=operator.itemgetter(1),
                                       reverse=True)[:20])
        negatives = dict([(k, abs(v)) for k, v in scoretable.items() if v < 0.0])
        negatives = OrderedDict(sorted(negatives.iteritems(),
                                       key=operator.itemgetter(1),
                                       reverse=True)[:20])

        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        html = template(self.request, 'search.html', {'expression': expression,
                                                      'parsed_expression': parsed_expression,
                                                      'positives': positives,
                                                      'negatives': negatives})
        set_response_body(self.response, html, head)


class WikiqueryHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        cache.create_prc()
        query = WikiPage.path_to_title(path)
        user = get_cur_user()
        result = WikiPage.wikiquery(query, user)
        view = self.request.GET.get('view', 'default')
        restype = get_restype(self.request)
        if restype == 'default' or restype == 'html':
            if view == 'bodyonly':
                html = template(self.request, 'bodyonly.html', {
                    'title': u'Search: %s ' % query,
                    'body': obj_to_html(result),
                })
            else:
                html = template(self.request, 'wikiquery.html', {
                    'query': query,
                    'result': obj_to_html(result),
                })
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, head)
        elif restype == 'json':
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(result), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)


class PageHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        if path == '':
            self.response.headers['Location'] = '/Home'
            if len(self.request.query):
                self.response.headers['Location'] += '?%s' % self.request.query
            self.response.status = 303
            return
        elif self.request.path_qs.find('%20') != -1:
            self.response.headers['Location'] = '%s' % self.request.path_qs.replace('%20', '_')
            self.response.status = 303
            return

        cache.create_prc()
        title = WikiPage.path_to_title(path)
        user = get_cur_user()
        restype = get_restype(self.request)
        view = self.request.GET.get('view', 'default')
        page = WikiPage.get_by_title(title)

        rev = self.request.GET.get('rev', 'latest')
        if rev == 'list':
            self.get_revision_list(restype, page, head)
            return

        if rev == 'latest':
            rev = '%d' % page.revision
        rev = int(rev)

        if rev != page.revision:
            page = page.revisions.filter(WikiPageRevision.revision == rev).get()

        if not page.can_read(user):
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, '403.html', {'page': page})
            set_response_body(self.response, html, False)
            return

        # custom content-type metadata?
        if restype == 'default' and view == 'default' and page.metadata['content-type'] != 'text/x-markdown':
            self.response.headers['Content-Type'] = '%s; charset=utf-8' % str(page.metadata['content-type'])
            set_response_body(self.response, WikiPage.remove_metadata(page.body), head)
            return

        if restype == 'default':
            if view == 'default':
                redirect = page.metadata.get('redirect', None)
                if redirect is not None:
                    self.response.headers['Location'] = '/' + WikiPage.title_to_path(redirect)
                    self.response.status = 303
                    return

                template_data = {
                    'page': page,
                    'message': self.response.headers.get('X-Message', None),
                }
                if page.metadata.get('schema', None) == 'Blog':
                    template_data['posts'] = WikiPage.get_published_posts(page.title, 20)
                elif page.revision == 0:
                    self.response.status_int = 404

                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                html = template(self.request, 'wikipage.html', template_data)
                set_response_body(self.response, html, head)
            elif view == 'edit':
                html = template(self.request, 'wikipage.form.html', {'page': page, 'conflict': None})
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                set_response_body(self.response, html, head)
            elif view == 'bodyonly':
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                html = template(self.request, 'bodyonly.html', {
                    'title': page.title,
                    'body': page.rendered_body,
                })
                set_response_body(self.response, html, head)
        elif restype == 'atom':
            pages = WikiPage.get_published_posts(page.title, 20)
            rendered = self._render_posts_atom(page.title, pages)
            self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
            set_response_body(self.response, rendered, head)
        elif restype == 'txt':
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            set_response_body(self.response, page.body, head)
        elif restype == 'json':
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            pagedict = {
                'title': page.title,
                'modifier': page.modifier.email() if page.modifier else None,
                'updated_at': format_iso_datetime(page.updated_at),
                'body': page.body,
                'revision': page.revision,
                'acl_read': page.acl_read,
                'acl_write': page.acl_write,
                'data': page.data,
            }
            set_response_body(self.response, json.dumps(pagedict), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_revision_list(self, restype, page, head):
        revisions = page.revisions.order(-WikiPageRevision.created_at)

        if restype == 'default':
            html = template(self.request, 'history.html', {'page': page, 'revisions': revisions})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, head)
        elif restype == 'json':
            revisions = [{'url': rev.absolute_url, 'title': rev.title} for rev in revisions]
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(revisions), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)
            return

    def post(self, path):
        method = self.request.GET.get('_method', 'POST')
        if method == 'DELETE':
            return self.delete(path)
        elif method == 'PUT':
            return self.put(path)

        cache.create_prc()
        title = WikiPage.path_to_title(path)

        user = get_cur_user()
        page = WikiPage.get_by_title(title)
        new_body = self.request.POST['body']
        comment = self.request.POST.get('comment', '')

        if not page.can_write(user):
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, '403.html', {'page': page})
            set_response_body(self.response, html, False)
            return

        try:
            page.update_content(page.body + new_body, page.revision, comment, user)
            self.response.location = page.absolute_url
            self.response.headers['X-Message'] = 'Successfully updated.'
            quoted_path = urllib2.quote(path.replace(' ', '_'))
            restype = get_restype(self.request)
            if restype == 'default':
                self.response.headers['Location'] = str('/' + quoted_path)
            else:
                self.response.headers['Location'] = str('/%s?_type=%s' % (quoted_path, restype))
            self.response.status = 303

        except ValueError as e:
            self.response.status = 406
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
            set_response_body(self.response, html, False)

    def put(self, path):
        cache.create_prc()
        title = WikiPage.path_to_title(path)

        user = get_cur_user()
        page = WikiPage.get_by_title(title)
        revision = int(self.request.POST['revision'])
        new_body = self.request.POST['body']
        comment = self.request.POST.get('comment', '')
        preview = self.request.POST.get('preview', '0')

        if preview == '1':
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, 'bodyonly.html', {
                'title': page.title,
                'body': page.preview_rendered_body(new_body)
            })
            set_response_body(self.response, html, False)
            return

        if not page.can_write(user):
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, '403.html', {'page': page})
            set_response_body(self.response, html, False)
            return

        try:
            page.update_content(new_body, revision, comment, user)
            self.response.location = page.absolute_url
            self.response.headers['X-Message'] = 'Successfully updated.'
            quoted_path = urllib2.quote(path.replace(' ', '_'))
            restype = get_restype(self.request)
            if restype == 'default':
                self.response.headers['Location'] = str('/' + quoted_path)
            else:
                self.response.headers['Location'] = str('/%s?_type=%s' % (quoted_path, restype))
            self.response.status = 303
        except ConflictError as e:
            self.response.status = 409
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, 'wikipage.form.html', {'page': page, 'conflict': e})
            set_response_body(self.response, html, False)
        except ValueError as e:
            self.response.status = 406
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
            set_response_body(self.response, html, False)

    def delete(self, path):
        cache.create_prc()
        title = WikiPage.path_to_title(path)

        page = WikiPage.get_by_title(title)
        user = get_cur_user()

        try:
            page.delete(user)
            self.response.status = 204
        except RuntimeError as e:
            self.response.status = 403
            html = template(self.request, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
            set_response_body(self.response, html, False)


class SpecialPageHandler(webapp2.RequestHandler):
    def post(self, path):
        cache.create_prc()
        user = get_cur_user()
        if path == 'preferences':
            self.post_preferences(user)
        else:
            self.abort(404)

    def post_preferences(self, user):
        if user is None:
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, '403.html', {'page': {
                'absolute_url': '/sp.preferences',
                'title': 'User preferences',
            }})
            set_response_body(self.response, html, False)
            return

        userpage_title = self.request.POST['userpage_title']
        UserPreferences.save(user, userpage_title)
        self.response.headers['X-Message'] = 'Successfully updated.'
        self.get_preferences(user, False)

    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        cache.create_prc()
        user = get_cur_user()
        title = WikiPage.path_to_title(path)

        if title == u'titles':
            self.get_titles(user, head)
        elif title == u'changes':
            self.get_changes(user, head)
        elif title == u'index':
            self.get_index(user, head)
        elif title == u'posts':
            self.get_posts(user, head)
        elif title == u'search':
            self.get_search(user, head)
        elif title == u'opensearch':
            self.get_opensearch(user, head)
        elif title == u'randomly update related pages':
            recent = self.request.GET.get('recent', '0')
            titles = WikiPage.randomly_update_related_links(50, recent == '1')
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('\n'.join(titles))
        elif title == u'preferences':
            self.get_preferences(user, head)
        elif title == u'rebuild data index':
            deferred.defer(WikiPage.rebuild_all_data_index, 0)
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Done! (queued)')
        elif title == u'fix suggested pages':
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            index = int(self.request.GET.get('index', '0'))
            pages = WikiPage.query().fetch(200, offset=index * 200)
            for page in pages:
                keys = [key for key in page.related_links.keys() if key.find('/') != -1]
                if len(keys) == 0:
                    continue
                else:
                    self.response.write('%s\n' % page.title)
                    for key in keys:
                        del page.related_links[key]
                        self.response.write('%s\n' % key)
                    page.put()
        elif title == u'fix comment':
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            index = int(self.request.GET.get('index', '0'))
            pages = WikiPage.query().fetch(100, offset=index * 100)
            for page in pages:
                page.comment = ''
                page.put()
        elif title == u'gcstest':
            import cloudstorage as gcs
            f = gcs.open(
                '/ecogwiki/test.txt', 'w',
                content_type='text/plain',
                retry_params=gcs.RetryParams(backoff_factor=1.1),
                options={'x-goog-acl': 'public-read'},
            )
            f.write('Hello')
            f.close()
            self.response.write('Done')
        else:
            self.abort(404)

    def get_preferences(self, user, head):
        if user is None:
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, '403.html', {
                'page': {
                    'absolute_url': '/sp.preferences',
                    'title': 'User preferences',
                }
            })
            set_response_body(self.response, html, False)
            return

        preferences = UserPreferences.get_by_email(user.email())
        rendered = template(self.request, 'wiki_sp_preferences.html', {
            'preferences': preferences,
            'message': self.response.headers.get('X-Message', None),
        })
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        set_response_body(self.response, rendered, head)

    def get_changes(self, user, head):
        restype = get_restype(self.request)
        email = user.email() if user is not None else 'None'
        rendered = None

        if restype == 'default':
            if rendered is None:
                pages = WikiPage.get_changes(user)
                rendered = template(self.request, 'wiki_sp_changes.html',
                                          {'pages': pages})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, rendered, head)
        elif restype == 'atom':
            if rendered is None:
                pages = WikiPage.get_changes(None, 3, include_body=True)
                config = WikiPage.get_config()
                host = self.request.host_url
                url = "%s/sp.changes?_type=atom" % host
                feed = AtomFeed(title="%s: changes" % config['service']['title'],
                                feed_url=url,
                                url="%s/" % host,
                                author=config['admin']['email'])
                for page in pages:
                    feed.add(title=page.title,
                             content_type="html",
                             content=page.rendered_body,
                             author=page.modifier,
                             url='%s%s' % (host, page.absolute_url),
                             updated=page.updated_at)
                rendered = feed.to_string()
            self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
            set_response_body(self.response, rendered, head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_posts(self, user, head):
        restype = get_restype(self.request)
        email = user.email() if user is not None else 'None'
        rendered = None

        if restype == 'default':
            if rendered is None:
                pages = WikiPage.get_published_posts(None, 200)
                rendered = template(self.request, 'wiki_sp_posts.html',
                                          {'pages': pages})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, rendered, head)
        elif restype == 'atom':
            if rendered is None:
                pages = WikiPage.get_published_posts(None, 20)
                rendered = self._render_posts_atom(None, pages)
            self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
            set_response_body(self.response, rendered, head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_index(self, user, head):
        restype = get_restype(self.request)
        if restype == 'default':
            pages = WikiPage.get_index(user)
            page_group = groupby(pages,
                                 lambda p: title_grouper(p.title))
            html = template(self.request, 'wiki_sp_index.html',
                                  {'page_group': page_group})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, head)
        elif restype == 'atom':
            pages = WikiPage.get_index(None)
            config = WikiPage.get_config()
            host = self.request.host_url
            url = "%s/sp.index?_type=atom" % host
            feed = AtomFeed(title="%s: title index" % config['service']['title'],
                            feed_url=url,
                            url="%s/" % host,
                            author=config['admin']['email'])
            for page in pages:
                feed.add(title=page.title,
                         content_type="html",
                         author=page.modifier,
                         url='%s%s' % (host, page.absolute_url),
                         updated=page.updated_at)
            self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
            set_response_body(self.response, feed.to_string(), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_search(self, user, head):
        restype = get_restype(self.request)
        resformat = self.request.GET.get('format', 'opensearch')
        q = self.request.GET.get('q', None)

        if restype == 'json' and resformat == 'opensearch':
            titles = WikiPage.get_titles(user)
            if q is not None and len(q) > 0:
                titles = [t for t in titles if t.find(q) != -1]
            self.response.headers['Content-Type'] = 'application/json'
            set_response_body(self.response, json.dumps([q, list(titles)]), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_opensearch(self, user, head):
        self.response.headers['Content-Type'] = 'text/xml'
        rendered = template(self.request, 'opensearch.xml', {})
        set_response_body(self.response, rendered, head)

    def get_titles(self, user, head):
        restype = get_restype(self.request)

        if restype == 'json':
            titles = WikiPage.get_titles(user)
            self.response.headers['Content-Type'] = 'application/json'
            set_response_body(self.response, json.dumps(list(titles)), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def _render_posts_atom(self, title, pages):
        host = self.request.host_url
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


def get_restype(req):
    return str(req.GET.get('_type', 'default'))


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
        preferences = UserPreferences.get_by_email(user.email())

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


def get_cur_user():
    user = users.get_current_user()
    # try oauth
    if user is None:
        try:
            oauth_user = oauth.get_current_user()
            is_local_dummy_user = oauth_user.user_id() == '0' and oauth_user.email() == 'example@example.com'
            if not is_local_dummy_user:
                user = oauth_user
        except oauth.OAuthRequestError as e:
            pass

    if user is not None:
        cache.add_recent_email(user.email())
    return user


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
            return '<a href="%s">%s</a>' % (to_path(o), o)
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
