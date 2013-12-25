# coding=utf-8
import json
import cache
import urllib2
import search
import operator
from collections import OrderedDict
from models import WikiPage, WikiPageRevision, ConflictError
from representations import Representation, EmptyRepresentation, JsonRepresentation, TemplateRepresentation, get_cur_user, get_restype, render_posts_atom, format_iso_datetime, template, set_response_body


class Resource(object):
    def __init__(self, req, res):
        self.user = get_cur_user()
        self.req = req
        self.res = res

    def get_representation(self, content):
        default_restype = 'html'
        default_view = 'default'
        restype = get_restype(self.req, default_restype)
        view = self.req.GET.get('view', default_view)
        try:
            method = getattr(self, 'represent_%s_%s' % (restype, view))
        except:
            try:
                method = getattr(self, 'represent_%s_%s' % (default_restype, view))
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
        cache.create_prc()
        self.path = path

    def represent_html_default(self, page):
        if page.metadata['content-type'] != 'text/x-markdown':
            content = WikiPage.remove_metadata(page.body)
            content_type = '%s; charset=utf-8' % str(page.metadata['content-type'])
            return Representation(content, content_type)

        if page.metadata.get('redirect', None) is not None:
            content_type = None
            content = None
            return Representation(content, content_type)
        else:
            content = {
                'page': page,
                'message': self.res.headers.get('X-Message', None),
            }
            content_type = 'text/html; charset=utf-8'
            if page.metadata.get('schema', None) == 'Blog':
                content['posts'] = page.get_posts(20)
            return TemplateRepresentation(content, content_type, self.req, 'wikipage.html')

    def represent_html_bodyonly(self, page):
        content = {
            'title': page.title,
            'body': page.rendered_body,
        }
        content_type = 'text/html; charset=utf-8'
        return TemplateRepresentation(content, content_type, self.req, 'wikipage_bodyonly.html')

    def represent_atom_default(self, page):
        content = render_posts_atom(self.req, page.title, page.get_posts(20))
        content_type = 'text/xml; charset=utf-8'
        return Representation(content, content_type)

    def represent_txt_default(self, page):
        content = page.body
        content_type = 'text/plain; charset=utf-8'
        return Representation(content, content_type)

    def represent_json_default(self, page):
        content = {
            'title': page.title,
            'modifier': page.modifier.email() if page.modifier else None,
            'updated_at': format_iso_datetime(page.updated_at),
            'body': page.body,
            'revision': page.revision,
            'acl_read': page.acl_read,
            'acl_write': page.acl_write,
            'data': page.data,
        }
        content_type = 'application/json; charset=utf-8'
        return Representation(content, content_type)

    def _403(self, page, head=False):
        self.res.status = 403
        self.res.headers['Content-Type'] = 'text/html; charset=utf-8'
        html = template(self.req, '403.html', {'page': page})
        set_response_body(self.res, html, head)


class PageResource(PageLikeResource):
    def load(self):
        return WikiPage.get_by_path(self.path)

    def get(self, head):
        page = self.load()

        if not page.can_read(self.user):
            self._403(head, page)
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
            html = template(self.req, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
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
            html = template(self.req, 'wikipage_bodyonly.html', {
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
            html = template(self.req, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
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
            html = template(self.req, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
            set_response_body(self.res, html, False)

    def represent_html_edit(self, page):
        if page.revision == 0 and self.req.GET.get('body'):
            page.body = self.req.GET.get('body')
        content = {'page': page}
        content_type = 'text/html; charset=utf-8'
        return TemplateRepresentation(content, content_type, self.req, 'wikipage.form.html')


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
            return

        representation = self.get_representation(page)
        representation.respond(self.res, head)


class RevisionListResource(Resource):
    def __init__(self, req, res, path):
        super(RevisionListResource, self).__init__(req, res)
        cache.create_prc()
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

    def get(self, head):
        representation = self.get_representation(self.load())
        representation.respond(self.res, head)

    def represent_html_default(self, content):
        content_type = 'text/html; charset=utf-8'
        return TemplateRepresentation(content, content_type, self.req, 'history.html')

    def represent_json_default(self, content):
        content = [
            {
                'revision': rev.revision,
                'url': rev.absolute_url,
                'created_at': format_iso_datetime(rev.created_at),
            }
            for rev in content['revisions']
        ]
        content_type = 'application/json; charset=utf-8'
        return JsonRepresentation(content, content_type)


class RelatedPagesResource(Resource):
    def __init__(self, req, res, path):
        super(RelatedPagesResource, self).__init__(req, res)
        cache.create_prc()
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

    def get(self, head):
        representation = self.get_representation(self.load())
        representation.respond(self.res, head)

    def represent_html_default(self, content):
        content_type = 'text/html; charset=utf-8'
        return TemplateRepresentation(content, content_type, self.req, 'search.html')

    def represent_json_default(self, content):
        content_type = 'application/json; charset=utf-8'
        return JsonRepresentation(content, content_type)
