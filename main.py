# -*- coding: utf-8 -*-
import sys
import webapp2


if 'lib' not in sys.path:
    sys.path[0:0] = ['lib']

VERSION = '0.0.1_20140202_5'

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
        'google_oauth2_web_client_id': '',
        'google_drive_folder': 'ecogwiki_public',
        'css_list': [
            '/statics/css/base.css',
        ],
        'default_permissions': {
            'read': ['all'],
            'write': ['login'],
        },
    }
}

app = webapp2.WSGIApplication([
    (ur'/sp\.(.*)', 'views.SpecialPageHandler'),
    (ur'/([+-].*)', 'views.RelatedPagesHandler'),
    (ur'/=(.*)', 'views.WikiqueryHandler'),
    (ur'/(.*)', 'views.PageHandler'),
], debug=True)
