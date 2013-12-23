# -*- coding: utf-8 -*-
import json
import cache
import search
import webapp2
import operator
from collections import OrderedDict
from models import WikiPage
from views.utils import get_restype, template, set_response_body


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
