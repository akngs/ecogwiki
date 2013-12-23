# -*- coding: utf-8 -*-
import json
import cache
import webapp2
import urllib2
from models import WikiPage, WikiPageRevision, ConflictError
from views.utils import get_cur_user, get_restype, template, set_response_body, render_posts_atom, format_iso_datetime


class PageHandler(webapp2.RequestHandler):
    def head(self, path):
        return self.get(path, True)

    def get(self, path, head=False):
        if path == '':
            self.response.location = '/Home'
            if len(self.request.query):
                self.response.location += '?%s' % self.request.query
            self.response.status = 303
            return
        elif self.request.path.find('%20') != -1:
            self.response.location = '%s' % self.request.path_qs.replace('%20', '_')
            self.response.status = 303
            return

        cache.create_prc()

        title = WikiPage.path_to_title(path)
        user = get_cur_user()
        page = WikiPage.get_by_title(title)
        restype = get_restype(self.request, 'html')
        view = self.request.GET.get('view', 'default')

        rev = self.request.GET.get('rev', 'latest')
        if rev == 'list':
            self.get_revision_list(restype, page, user, head)
        else:
            if rev == 'latest':
                rev = '%d' % page.revision
            rev = int(rev)
            if rev != page.revision:
                page = page.revisions.filter(WikiPageRevision.revision == rev).get()
            self.get_page(restype, view, page, user, head)

    def get_page(self, restype, view, page, user, head):
        if not page.can_read(user):
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, '403.html', {'page': page})
            set_response_body(self.response, html, False)
            return

        # custom content-type metadata?
        if restype == 'html' and view == 'default' and page.metadata['content-type'] != 'text/x-markdown':
            self.response.headers['Content-Type'] = '%s; charset=utf-8' % str(page.metadata['content-type'])
            set_response_body(self.response, WikiPage.remove_metadata(page.body), head)
            return

        if restype == 'html':
            if view == 'default':
                redirect = page.metadata.get('redirect', None)
                if redirect is not None:
                    self.response.location = '/' + WikiPage.title_to_path(redirect)
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

                html = template(self.request, 'wikipage.html', template_data)
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                set_response_body(self.response, html, head)
            elif view == 'edit':
                # insert body from params if revision is 0
                if page.revision == 0 and self.request.GET.get('body'):
                    page.body = self.request.GET.get('body')
                html = template(self.request, 'wikipage.form.html', {'page': page, 'conflict': None})
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                set_response_body(self.response, html, head)
            elif view == 'bodyonly':
                html = template(self.request, 'wikipage_bodyonly.html', {
                    'title': page.title,
                    'body': page.rendered_body,
                })
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                set_response_body(self.response, html, head)
        elif restype == 'atom':
            pages = WikiPage.get_published_posts(page.title, 20)
            rendered = render_posts_atom(self.request, page.title, pages)
            self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
            set_response_body(self.response, rendered, head)
        elif restype == 'txt':
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            set_response_body(self.response, page.body, head)
        elif restype == 'json':
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
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(pagedict), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

    def get_revision_list(self, restype, page, user, head):
        revisions = [
            r for r in page.revisions.order(-WikiPageRevision.created_at)
            if r.can_read(user)
        ]

        if restype == 'html':
            html = template(self.request, 'history.html', {'page': page, 'revisions': revisions})
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, head)
        elif restype == 'json':
            revisions = [
                {
                    'revision': rev.revision,
                    'url': rev.absolute_url,
                    'created_at': format_iso_datetime(rev.created_at),
                }
                for rev in revisions
            ]
            self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
            set_response_body(self.response, json.dumps(revisions), head)
        else:
            self.abort(400, 'Unknown type: %s' % restype)

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
            html = template(self.request, '403.html', {'page': page})
            self.response.status = 403
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, False)
            return

        try:
            page.update_content(page.body + new_body, page.revision, comment, user)
            quoted_path = urllib2.quote(path.replace(' ', '_'))
            restype = get_restype(self.request, 'html')
            if restype == 'html':
                self.response.location = str('/' + quoted_path)
            else:
                self.response.location = str('/%s?_type=%s' % (quoted_path, restype))
            self.response.status = 303
            self.response.headers['X-Message'] = 'Successfully updated.'
        except ValueError as e:
            html = template(self.request, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
            self.response.status = 406
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
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
        partial = self.request.GET.get('partial', 'all')

        if preview == '1':
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            html = template(self.request, 'wikipage_bodyonly.html', {
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
            page.update_content(new_body, revision, comment, user, partial=partial)
            self.response.headers['X-Message'] = 'Successfully updated.'

            if partial == 'all':
                quoted_path = urllib2.quote(path.replace(' ', '_'))
                self.response.status = 303
                restype = get_restype(self.request, 'html')
                if restype == 'html':
                    self.response.location = str('/' + quoted_path)
                else:
                    self.response.location = str('/%s?_type=%s' % (quoted_path, restype))
            else:
                self.response.status = 200
                self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
                self.response.write(json.dumps({'revision': page.revision}))
        except ConflictError as e:
            html = template(self.request, 'wikipage.form.html', {'page': page, 'conflict': e})
            self.response.status = 409
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            set_response_body(self.response, html, False)
        except ValueError as e:
            html = template(self.request, 'error_with_messages.html', {'page': page, 'errors': [e.message]})
            self.response.status = 406
            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
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
