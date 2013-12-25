# -*- coding: utf-8 -*-
import json
import cache
import schema
import search
import urllib2
import webapp2
import operator
from pyatom import AtomFeed
from itertools import groupby
from collections import OrderedDict
from google.appengine.ext import deferred
from models import WikiPage, UserPreferences, title_grouper, get_cur_user
from resources import RedirectResource, PageResource, RevisionResource, RevisionListResource
from representations import template, set_response_body, get_restype, render_posts_atom, obj_to_html


class PageHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        if path == '':
            resource = RedirectResource(self.request, self.response, '/Home')
        elif self.request.path.find('%20') != -1:
            resource = RedirectResource(self.request, self.response, '/%s' % path.replace(' ', '_'))
        elif self.request.GET.get('rev') == 'list':
            resource = RevisionListResource(self.request, self.response, path)
        elif self.request.GET.get('rev', '') != '':
            resource = RevisionResource(self.request, self.response, path, self.request.GET.get('rev', ''))
        else:
            resource = PageResource(self.request, self.response, path)
        resource.get(head)

    def post(self, path):
        method = self.request.GET.get('_method', 'POST')
        if method == 'DELETE':
            return self.delete(path)
        elif method == 'PUT':
            return self.put(path)

        resource = PageResource(self.request, self.response, path)
        resource.post()

    def put(self, path):
        resource = PageResource(self.request, self.response, path)
        resource.put()

    def delete(self, path):
        resource = PageResource(self.request, self.response, path)
        resource.delete()


class RelatedPagesHandler(webapp2.RequestHandler):
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
        result = {
            'expression': expression,
            'parsed_expression': parsed_expression,
            'positives': positives,
            'negatives': negatives
        }

        restype = get_restype(self.request, 'html')
        if restype == 'html':
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, 'search.html', result)
            set_response_body(self.response, html, head)
        elif restype == 'json':
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(result), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)


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
            html = template(self.request, '403.html', {'page': {
                'absolute_url': '/sp.preferences',
                'title': 'User preferences',
            }})
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
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
            self.get_opensearch(head)
        elif title == u'randomly update related pages':
            recent = self.request.GET.get('recent', '0')
            titles = WikiPage.randomly_update_related_links(50, recent == '1')
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('\n'.join(titles))
        elif title == u'preferences':
            self.get_preferences(user, head)
        elif title.startswith(u'schema/'):
            self.get_schema(title.split(u'/')[1:], head)
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
        elif title == u'schema':
            itemtype = self.request.GET.get('itemtype', 'Article')
            itemschema = schema.get_schema(itemtype)

            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write(json.dumps(itemschema))
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

    def get_schema(self, tokens, head):
        key1, key2 = tokens
        if key1 == u'types':
            data = schema.get_schema(key2)
        elif key1 == u'properties':
            data = schema.get_property(key2)
        else:
            self.abort(400, 'Unknown key: %s' % key1)
            return

        restype = get_restype(self.request, 'json')
        if restype == 'html':
            self.abort(400, 'Unknown type: %s' % restype)
            # view = self.request.GET.get('view', 'default')
            # if view == 'default':
            #     html = template(self.request, 'schema.html', {
            #         'schema': u'%s / %s' % (key1, key2),
            #         'data': obj_to_html(data),
            #     })
            #     self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            #     set_response_body(self.response, html, head)
            # elif view == 'bodyonly':
            #     html = template(self.request, 'wikipage_bodyonly.html', {
            #         'schema': u'%s / %s' % (key1, key2),
            #         'data': obj_to_html(data),
            #     })
            #     self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            #     set_response_body(self.response, html, head)
            # else:
            #     self.abort(400, 'Unknown view: %s' % view)
        elif restype == 'json':
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(data), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_changes(self, user, head):
        restype = get_restype(self.request, 'html')

        if restype == 'html':
            pages = WikiPage.get_changes(user)
            rendered = template(self.request, 'wiki_sp_changes.html',
                                {'pages': pages})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, rendered, head)
        elif restype == 'atom':
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
        restype = get_restype(self.request, 'html')

        if restype == 'html':
            pages = WikiPage.get_posts_of(None, 200)
            rendered = template(self.request, 'wiki_sp_posts.html',
                                {'pages': pages})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, rendered, head)
        elif restype == 'atom':
            pages = WikiPage.get_posts_of(None, 20)
            rendered = render_posts_atom(self.request, None, pages)
            self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
            set_response_body(self.response, rendered, head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_index(self, user, head):
        restype = get_restype(self.request, 'html')
        if restype == 'html':
            pages = WikiPage.get_index(user)
            page_group = groupby(pages,
                                 lambda p: title_grouper(p.title))
            html = template(self.request, 'wiki_sp_index.html', {'page_group': page_group})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, head)
        elif restype == 'atom':
            pages = WikiPage.get_index()
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
        q = self.request.GET.get('q', '')
        if len(q) == 0:
            self.abort(400)
            return

        title = WikiPage.path_to_title(q.encode('utf-8'))
        page = WikiPage.get_by_title(title)
        restype = get_restype(self.request, 'html')

        if restype == 'html':
            redir = self.request.GET.get('redir', '0') == '1' and page.revision != 0
            if redir:
                quoted_path = urllib2.quote(q.encode('utf8').replace(' ', '_'))
                self.response.location = '/' + quoted_path
                self.response.status = 303
            else:
                view = self.request.GET.get('view', 'default')
                if view == 'default':
                    html = template(self.request, 'wiki_sp_search.html', {'q': q, 'page': page})
                    self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                    set_response_body(self.response, html, head)
                elif view == 'bodyonly':
                    html = template(self.request, 'wiki_sp_search_bodyonly.html', {'q': q, 'page': page})
                    self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                    set_response_body(self.response, html, head)
        elif restype == 'json':
            titles = WikiPage.get_titles(user)
            if q is not None and len(q) > 0:
                titles = [t for t in titles if t.find(title) != -1]
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps([q, list(titles)]), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_opensearch(self, head):
        self.response.headers['Content-Type'] = 'text/xml'
        rendered = template(self.request, 'opensearch.xml', {})
        set_response_body(self.response, rendered, head)

    def get_titles(self, user, head):
        restype = get_restype(self.request, 'json')

        if restype == 'json':
            titles = WikiPage.get_titles(user)
            self.response.headers['Content-Type'] = 'application/json'
            set_response_body(self.response, json.dumps(list(titles)), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)


class WikiqueryHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        cache.create_prc()
        query = WikiPage.path_to_title(path)
        user = get_cur_user()
        view = self.request.GET.get('view', 'default')
        restype = get_restype(self.request, 'html')
        result = WikiPage.wikiquery(query, user)

        if restype == 'html':
            if view == 'default':
                html = template(self.request, 'wikiquery.html', {
                    'query': query,
                    'result': obj_to_html(result),
                })
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                set_response_body(self.response, html, head)
            elif view == 'bodyonly':
                html = template(self.request, 'wikipage_bodyonly.html', {
                    'title': u'Search: %s ' % query,
                    'body': obj_to_html(result),
                })
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                set_response_body(self.response, html, head)
            else:
                self.abort(400, 'Unknown view: %s' % view)
        elif restype == 'json':
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(result), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)
