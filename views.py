# -*- coding: utf-8 -*-
import json
import cache
import schema
import webapp2
from pyatom import AtomFeed
from google.appengine.ext import deferred
from models import WikiPage, UserPreferences, get_cur_user
from resources import RedirectResource, PageResource, RevisionResource, RevisionListResource, RelatedPagesResource, WikiqueryResource, TitleListResource, SearchResultResource, TitleIndexResource, PostListResource, ChangeListResource
from representations import template, set_response_body, get_restype, TemplateRepresentation


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
        resource = RelatedPagesResource(self.request, self.response, path)
        resource.get(head)


class WikiqueryHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        resource = WikiqueryResource(self.request, self.response, path)
        resource.get(head)


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
        user = get_cur_user()
        title = WikiPage.path_to_title(path)

        if title == u'titles':
            resource = TitleListResource(self.request, self.response)
            resource.get(head)
        elif title == u'changes':
            resource = ChangeListResource(self.request, self.response)
            resource.get(head)
        elif title == u'index':
            resource = TitleIndexResource(self.request, self.response)
            resource.get(head)
        elif title == u'posts':
            resource = PostListResource(self.request, self.response)
            resource.get(head)
        elif title == u'search':
            resource = SearchResultResource(self.request, self.response)
            resource.get(head)
        elif title == u'opensearch':
            representation = TemplateRepresentation({}, self.request, 'opensearch.xml')
            representation.respond(self.response, head)
        elif title == u'preferences':
            cache.create_prc()
            self.get_preferences(user, head)
        elif title.startswith(u'schema/'):
            cache.create_prc()
            self.get_schema(title.split(u'/')[1:], head)
        elif title == u'randomly update related pages':
            cache.create_prc()
            recent = self.request.GET.get('recent', '0')
            titles = WikiPage.randomly_update_related_links(50, recent == '1')
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('\n'.join(titles))
        elif title == u'schema':
            cache.create_prc()
            itemtype = self.request.GET.get('itemtype', 'Article')
            itemschema = schema.get_schema(itemtype)

            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write(json.dumps(itemschema))
        elif title == u'rebuild data index':
            cache.create_prc()
            deferred.defer(WikiPage.rebuild_all_data_index, 0)
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Done! (queued)')
        elif title == u'fix suggested pages':
            cache.create_prc()
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
            cache.create_prc()
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            index = int(self.request.GET.get('index', '0'))
            pages = WikiPage.query().fetch(100, offset=index * 100)
            for page in pages:
                page.comment = ''
                page.put()
        elif title == u'gcstest':
            import cloudstorage as gcs
            cache.create_prc()
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
