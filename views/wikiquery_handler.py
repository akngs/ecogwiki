# -*- coding: utf-8 -*-
import json
import cache
import webapp2
from models import WikiPage
from views.utils import get_restype, get_cur_user, template, obj_to_html, set_response_body


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
