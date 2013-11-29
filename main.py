import sys
import webapp2


if 'lib' not in sys.path:
    sys.path[0:0] = ['lib']

VERSION = '0.0.1_20131129_4'

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
}

app = webapp2.WSGIApplication([
    (ur'/(.*)', 'views.WikiPageHandler', 'wikipage'),
], debug=True)
