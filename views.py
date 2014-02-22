# -*- coding: utf-8 -*-
import webapp2
import caching
from models import WikiPage
from google.appengine.ext import deferred
from representations import TemplateRepresentation
from resources import RedirectResource, PageResource, RevisionResource, RevisionListResource,\
    RelatedPagesResource, WikiqueryResource, TitleListResource, SearchResultResource,\
    TitleIndexResource, PostListResource, ChangeListResource, UserPreferencesResource,\
    SchemaResource


class PageHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        if path == '':
            resource = RedirectResource(self.request, self.response, '/Home')
        elif self.request.path.find(' ') != -1:
            resource = RedirectResource(self.request, self.response, '/%s' % WikiPage.title_to_path(path))
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
        method = self.request.GET.get('_method', 'POST')
        if method == 'DELETE':
            return self.delete(path)
        elif method == 'PUT':
            return self.put(path)

        if path == 'preferences':
            self.post_preferences()
        else:
            self.abort(404)

    def delete(self, _):
        self.abort(405)

    def put(self, _):
        self.abort(405)

    def post_preferences(self):
        resource = UserPreferencesResource(self.request, self.response)
        resource.post()

    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        if path == u'titles':
            resource = TitleListResource(self.request, self.response)
            resource.get(head)
        elif path == u'changes':
            resource = ChangeListResource(self.request, self.response)
            resource.get(head)
        elif path == u'index':
            resource = TitleIndexResource(self.request, self.response)
            resource.get(head)
        elif path == u'posts':
            resource = PostListResource(self.request, self.response)
            resource.get(head)
        elif path == u'search':
            resource = SearchResultResource(self.request, self.response)
            resource.get(head)
        elif path == u'preferences':
            resource = UserPreferencesResource(self.request, self.response)
            resource.get(head)
        elif path.startswith(u'schema/'):
            resource = SchemaResource(self.request, self.response, path)
            resource.get(head)
        elif path == u'opensearch':
            representation = TemplateRepresentation({}, self.request, 'opensearch.xml')
            representation.respond(self.response, head)
        elif path == u'flush_cache':
            caching.flush_all()
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Done!')
        elif path == u'randomly_update_related_pages':
            caching.create_prc()
            recent = self.request.GET.get('recent', '0')
            titles = WikiPage.randomly_update_related_links(50, recent == '1')
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('\n'.join(titles))
        elif path == u'rebuild_data_index':
            deferred.defer(WikiPage.rebuild_all_data_index, 0)
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Done! (queued)')
        else:
            self.abort(404)
