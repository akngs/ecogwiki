# -*- coding: utf-8 -*-
import sys
import webapp2


if 'lib' not in sys.path:
    sys.path[0:0] = ['lib']

VERSION = '0.0.1_20140115_1'

DEFAULT_CONFIG = {
    'navigation': [
        {
            'name': 'Home',
            'url': '/Home',
        },
        {
            'name': 'Changes',
            'url': '/sp.changes',
            'shortcut': 'C',
        },
    ],
    'admin': {
        'email': '',
        'gplus_url': '',
        'twitter': '',
    },
    'service': {
        'title': '',
        'domain': '',
        'fb_app_id': '',
        'ga_profile_id': '',
        'ga_classic_profile_id': '',
        'css_list': [
            '/statics/css/base.css',
        ],
        'default_permissions': {
            'read': ['all'],
            'write': ['login'],
        },
    },
    'highlight': {
        'style': 'default',
        'supported_languages': [
            'sh',
            'csharp',
            'c++',
            'css',
            'coffeescript',
            'diff',
            'html',
            'xml',
            'json',
            'java',
            'javascript',
            'makefile',
            'markdown',
            'objectivec',
            'php',
            'perl',
            'python',
            'ruby',
            'sql',
        ]
    }
}

app = webapp2.WSGIApplication([
    (ur'/sp\.(.*)', 'views.SpecialPageHandler'),
    (ur'/([+-].*)', 'views.RelatedPagesHandler'),
    (ur'/=(.*)', 'views.WikiqueryHandler'),
    (ur'/(.*)', 'views.PageHandler'),
], debug=True)
