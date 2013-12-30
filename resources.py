# coding=utf-8
import json
import urllib2
import search
import schema
import operator
from pyatom import AtomFeed
from itertools import groupby
from collections import OrderedDict
from models.utils import title_grouper
from models import WikiPage, WikiPageRevision, ConflictError, UserPreferences
from representations import Representation, EmptyRepresentation, JsonRepresentation, TemplateRepresentation, get_cur_user, format_iso_datetime, template


class Resource(object):
    def __init__(self, req, res, default_restype='html', default_view='default'):
        self.user = get_cur_user()
        self.req = req
        self.res = res
        self.default_restype = default_restype
        self.default_view = default_view

    def load(self):
        """Load data related to this resource"""
        return None

    def get(self, head):
        """Default implementation of GET"""
        representation = self.get_representation(self.load())
        representation.respond(self.res, head)

    def get_representation(self, content):
        restype = get_restype(self.req, self.default_restype)
        view = self.req.GET.get('view', self.default_view)
        try:
            method = getattr(self, 'represent_%s_%s' % (restype, view))
        except:
            try:
                method = getattr(self, 'represent_%s_%s' % (self.default_restype, view))
            except:
                method = None

        if method is not None:
            return method(content)
        else:
            return EmptyRepresentation(400)


class RedirectResource(Resource):
    def __init__(self, req, res, location):
        super(RedirectResource, self).__init__(req, res)
        self._location = location

    def get(self, head):
        self.res.location = self._location
        if len(self.req.query):
            self.res.location += '?%s' % self.req.query
        self.res.status = 303


class PageLikeResource(Resource):
    def __init__(self, req, res, path):
        super(PageLikeResource, self).__init__(req, res)
        self.path = path

    def represent_html_default(self, page):
        if page.metadata['content-type'] != 'text/x-markdown':
            content = WikiPage.remove_metadata(page.body)
            content_type = '%s; charset=utf-8' % str(page.metadata['content-type'])
            return Representation(content, content_type)

        if page.metadata.get('redirect', None) is not None:
            return Representation(None, None)
        else:
            content = {
                'page': page,
                'message': self.res.headers.get('X-Message', None),
            }
            if page.metadata.get('schema', None) == 'Blog':
                content['posts'] = page.get_posts(20)
            return TemplateRepresentation(content, self.req, 'wikipage.html')

    def represent_html_bodyonly(self, page):
        content = {
            'title': page.title,
            'body': page.rendered_body,
        }
        return TemplateRepresentation(content, self.req, 'generic_bodyonly.html')

    def represent_atom_default(self, page):
        content = render_posts_atom(self.req, page.title, page.get_posts(20))
        return Representation(content, 'text/xml; charset=utf-8')

    def represent_txt_default(self, page):
        return Representation(page.body, 'text/plain; charset=utf-8')

    def represent_json_default(self, page):
        content = {
            'title': page.title,
            'modifier': page.modifier.email() if page.modifier else None,
            'updated_at': format_iso_datetime(page.updated_at),
            'body': page.body,
            'revision': page.revision,
            'acl_read': page.acl_read,
            'acl_write': page.acl_write,
            'data': page.rawdata,
        }
        return JsonRepresentation(content)

    def _403(self, page, head=False):
        self.res.status = 403
        self.res.headers['Content-Type'] = 'text/html; charset=utf-8'
        html = template(self.req, 'error.html', {
            'page': page,
            'description': 'You don\'t have a permission',
            'errors': [],
        })
        set_response_body(self.res, html, head)


class PageResource(PageLikeResource):
    def load(self):
        return WikiPage.get_by_path(self.path)

    def get(self, head):
        page = self.load()

        if not page.can_read(self.user):
            self._403(page, head)
            return

        if get_restype(self.req, 'html') == 'html':
            redirect = page.metadata.get('redirect', None)
            if redirect is not None:
                self.res.location = '/' + WikiPage.title_to_path(redirect)
                self.res.status = 303
                return

        representation = self.get_representation(page)
        representation.respond(self.res, head)

    def post(self):
        page = self.load()

        if not page.can_write(self.user):
            self._403(page)
            return

        new_body = self.req.POST['body']
        comment = self.req.POST.get('comment', '')

        try:
            page.update_content(page.body + new_body, page.revision, comment, self.user)
            quoted_path = urllib2.quote(self.path.replace(' ', '_'))
            restype = get_restype(self.req, 'html')
            if restype == 'html':
                self.res.location = str('/' + quoted_path)
            else:
                self.res.location = str('/%s?_type=%s' % (quoted_path, restype))
            self.res.status = 303
            self.res.headers['X-Message'] = 'Successfully updated.'
        except ValueError as e:
            html = template(self.req, 'error.html', {
                'page': page,
                'description': 'Cannot accept the data for following reasons',
                'errors': [e.message]
            })
            self.res.status = 406
            self.res.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.res, html, False)

    def put(self):
        page = self.load()

        revision = int(self.req.POST['revision'])
        new_body = self.req.POST['body']
        comment = self.req.POST.get('comment', '')
        preview = self.req.POST.get('preview', '0')
        partial = self.req.GET.get('partial', 'all')

        if preview == '1':
            self.res.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.req, 'generic_bodyonly.html', {
                'title': page.title,
                'body': page.preview_rendered_body(new_body)
            })
            set_response_body(self.res, html, False)
            return

        if not page.can_write(self.user):
            self._403(page)
            return

        try:
            page.update_content(new_body, revision, comment, self.user, partial=partial)
            self.res.headers['X-Message'] = 'Successfully updated.'

            if partial == 'all':
                quoted_path = urllib2.quote(self.path.replace(' ', '_'))
                self.res.status = 303
                restype = get_restype(self.req, 'html')
                if restype == 'html':
                    self.res.location = str('/' + quoted_path)
                else:
                    self.res.location = str('/%s?_type=%s' % (quoted_path, restype))
            else:
                self.res.status = 200
                self.res.headers['Content-Type'] = 'application/json; charset=utf-8'
                self.res.write(json.dumps({'revision': page.revision}))
        except ConflictError as e:
            html = template(self.req, 'wikipage.form.html', {'page': page, 'conflict': e})
            self.res.status = 409
            self.res.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.res, html, False)
        except ValueError as e:
            html = template(self.req, 'error.html', {
                'page': page,
                'description': 'Cannot accept the data for following reasons',
                'errors': [e.message]
            })
            self.res.status = 406
            self.res.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.res, html, False)

    def delete(self):
        page = self.load()

        try:
            page.delete(self.user)
            self.res.status = 204
        except RuntimeError as e:
            self.res.status = 403
            html = template(self.req, 'error.html', {
                'page': page,
                'description': 'You don\'t have a permission to delete the page',
                'errors': [e.message]
            })
            set_response_body(self.res, html, False)

    def represent_html_edit(self, page):
        if page.revision == 0 and self.req.GET.get('body'):
            page.body = self.req.GET.get('body')
        return TemplateRepresentation({'page': page}, self.req, 'wikipage.form.html')


class RevisionResource(PageLikeResource):
    def __init__(self, req, res, path, revid):
        super(RevisionResource, self).__init__(req, res, path)
        self._revid = revid

    def load(self):
        page = WikiPage.get_by_path(self.path)

        rev = self._revid
        if rev == 'latest':
            rev = page.revision
        else:
            rev = int(rev)
        return page.revisions.filter(WikiPageRevision.revision == rev).get()

    def get(self, head):
        page = self.load()

        if not page.can_read(self.user):
            self._403(page, head)
        else:
            representation = self.get_representation(page)
            representation.respond(self.res, head)


class RevisionListResource(Resource):
    def __init__(self, req, res, path):
        super(RevisionListResource, self).__init__(req, res)
        self.path = path

    def load(self):
        page = WikiPage.get_by_path(self.path)
        revisions = [
            r for r in page.revisions.order(-WikiPageRevision.created_at)
            if r.can_read(self.user)
        ]
        return {
            'page': page,
            'revisions': revisions,
        }

    def represent_html_default(self, content):
        return TemplateRepresentation(content, self.req, 'history.html')

    def represent_json_default(self, content):
        content = [
            {
                'revision': rev.revision,
                'url': rev.absolute_url,
                'created_at': format_iso_datetime(rev.created_at),
            }
            for rev in content['revisions']
        ]
        return JsonRepresentation(content)


class RelatedPagesResource(Resource):
    def __init__(self, req, res, path):
        super(RelatedPagesResource, self).__init__(req, res)
        self.path = path

    def load(self):
        expression = WikiPage.path_to_title(self.path)
        scoretable = WikiPage.search(expression)
        parsed_expression = search.parse_expression(expression)
        positives = dict([(k, v) for k, v in scoretable.items() if v >= 0.0])
        positives = OrderedDict(sorted(positives.iteritems(),
                                       key=operator.itemgetter(1),
                                       reverse=True)[:20])
        negatives = dict([(k, abs(v)) for k, v in scoretable.items() if v < 0.0])
        negatives = OrderedDict(sorted(negatives.iteritems(),
                                       key=operator.itemgetter(1),
                                       reverse=True)[:20])
        return {
            'expression': expression,
            'parsed_expression': parsed_expression,
            'positives': positives,
            'negatives': negatives,
        }

    def represent_html_default(self, content):
        return TemplateRepresentation(content, self.req, 'search.html')

    def represent_json_default(self, content):
        return JsonRepresentation(content)


class WikiqueryResource(Resource):
    def __init__(self, req, res, path):
        super(WikiqueryResource, self).__init__(req, res)
        self.path = path

    def load(self):
        query = WikiPage.path_to_title(self.path)
        return {
            'result': WikiPage.wikiquery(query, self.user),
            'query': query
        }

    def represent_html_default(self, content):
        content = {
            'title': content['query'],
            'body': schema.to_html(content['result']),
        }
        return TemplateRepresentation(content, self.req, 'generic.html')

    def represent_html_bodyonly(self, content):
        content = {
            'title': u'Search: %s ' % content['query'],
            'body': schema.to_html(content['result']),
        }
        return TemplateRepresentation(content, self.req, 'generic_bodyonly.html')

    def represent_json_default(self, content):
        return JsonRepresentation(content)


class TitleListResource(Resource):
    def __init__(self, req, res):
        super(TitleListResource, self).__init__(req, res, default_restype='json')

    def load(self):
        return list(WikiPage.get_titles(self.user))

    def represent_json_default(self, titles):
        return JsonRepresentation(titles)


class SearchResultResource(Resource):
    def load(self):
        query = self.req.GET.get('q', '')
        if len(query) == 0:
            return {
                'query': query,
                'page': None,
            }
        else:
            return {
                'query': query,
                'page': WikiPage.get_by_title(query),
            }

    def get(self, head):
        content = self.load()
        if get_restype(self.req, 'html') == 'html':
            redir = self.req.GET.get('redir', '0') == '1' and content['page'].revision != 0
            if redir:
                quoted_path = urllib2.quote(content['query'].encode('utf8').replace(' ', '_'))
                self.res.location = '/' + quoted_path
                self.res.status = 303
                return

        representation = self.get_representation(content)
        representation.respond(self.res, head)

    def represent_html_default(self, content):
        return TemplateRepresentation(content, self.req, 'sp_search.html')

    def represent_html_bodyonly(self, content):
        return TemplateRepresentation(content, self.req, 'sp_search_bodyonly.html')

    def represent_json_default(self, content):
        if content['query'] is None or len(content['query']) == 0:
            titles = []
        else:
            titles = WikiPage.get_titles(self.user)
            titles = [t for t in titles if t.find(content['query']) != -1]

        return JsonRepresentation([content['query'], titles])


class TitleIndexResource(Resource):
    def load(self):
        return WikiPage.get_index(self.user)

    def represent_html_default(self, pages):
        page_group = groupby(pages, lambda p: title_grouper(p.title))
        return TemplateRepresentation({'page_group': page_group}, self.req, 'sp_index.html')

    def represent_atom_default(self, pages):
        config = WikiPage.get_config()
        host = self.req.host_url
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
        return Representation(feed.to_string(), 'text/xml; charset=utf-8')


class PostListResource(Resource):
    def load(self):
        return WikiPage.get_posts_of(None, 20)

    def represent_html_default(self, posts):
        return TemplateRepresentation({'pages': posts}, self.req, 'sp_posts.html')

    def represent_atom_default(self, posts):
        return Representation(render_posts_atom(self.req, None, posts), 'text/xml; charset=utf-8')


class ChangeListResource(Resource):
    def load(self):
        return WikiPage.get_changes(self.user)

    def represent_html_default(self, pages):
        return TemplateRepresentation({'pages': pages}, self.req, 'sp_changes.html')

    def represent_atom_default(self, pages):
        config = WikiPage.get_config()
        host = self.req.host_url
        url = "%s/sp.changes?_type=atom" % host
        feed = AtomFeed(title="%s: changes" % config['service']['title'],
                        feed_url=url,
                        url="%s/" % host,
                        author=config['admin']['email'])
        for page in pages:
            feed.add(title=page.title,
                     content_type="html",
                     author=page.modifier,
                     url='%s%s' % (host, page.absolute_url),
                     updated=page.updated_at)
        return Representation(feed.to_string(), 'text/xml; charset=utf-8')


class UserPreferencesResource(Resource):
    def load(self):
        if self.user is None:
            return None
        else:
            return UserPreferences.get_by_user(self.user)

    def get(self, head):
        if self.user is None:
            self.res.status = 403
            TemplateRepresentation({
                'page': {
                    'absolute_url': '/sp.preferences',
                    'title': 'User preferences',
                },
                'description': 'You don\'t have a permission',
                'errors': [],
            }, self.req, 'error.html').respond(self.res, head)
            return
        else:
            representation = self.get_representation(self.load())
            representation.respond(self.res, head)

    def post(self):
        if self.user is None:
            self.res.status = 403
            TemplateRepresentation({
                'page': {
                    'absolute_url': '/sp.preferences',
                    'title': 'User preferences',
                },
                'description': 'You don\'t have a permission',
                'errors': [],
            }, self.req, 'error.html').respond(self.res, False)
            return

        prefs = self.load()
        prefs.userpage_title = self.req.POST['userpage_title']
        prefs.put()

        self.res.headers['X-Message'] = 'Successfully updated.'
        representation = self.get_representation(prefs)
        representation.respond(self.res, False)

    def represent_html_default(self, prefs):
        return TemplateRepresentation({
            'preferences': prefs,
            'message': self.res.headers.get('X-Message', None),
        }, self.req, 'sp_preferences.html')


class SchemaResource(Resource):
    def __init__(self, req, res, path):
        super(SchemaResource, self).__init__(req, res)
        self.path = path

    def load(self):
        tokens = self.path.split('/')[1:]
        if tokens[0] == 'types':
            return schema.get_schema(tokens[1])
        elif tokens[0] == 'properties':
            return schema.get_property(tokens[1])
        else:
            return None

    def represent_html_default(self, data):
        content = {
            'title': data['id'],
            'body': schema.to_html(data),
        }
        return TemplateRepresentation(content, self.req, 'generic.html')

    def represent_html_bodyonly(self, data):
        content = {
            'title': data['id'],
            'body': schema.to_html(data),
        }
        return TemplateRepresentation(content, self.req, 'generic_bodyonly.html')

    def represent_json_default(self, data):
        return JsonRepresentation(data)


def get_restype(req, default):
    return str(req.GET.get('_type', default))


def set_response_body(res, resbody, head):
    if head:
        res.headers['Content-Length'] = str(len(resbody))
    else:
        res.write(resbody)


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
