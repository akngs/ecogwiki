SUPPORTED_SCHEMA = {
    'Article': {
        'parent': 'CreativeWork',
        'properties': {
            'relatedTo': (u'Related pages', u'Related to'),
        }
    },
    'Blog': {
        'parent': 'CreativeWork',
        'properties': {
            'relatedTo': (u'Related blogs', u'Related to'),
        }
    },
    'Book': {
        'parent': 'CreativeWork',
        'properties': {
            'author': (u'Author of', u'Author'),
            'datePublished': (u'Publications', u'Published date'),
            'dateModified': (u'Publications (revised)', u'Revised date'),
            'relatedTo': (u'Related books', u'Related to'),
        }
    },
    'Code': {
        'parent': 'CreativeWork',
        'properties': {
            'programmingLanguage': (u'Codes, snippiets or libraries', u'Codes'),
            'relatedTo': (u'Related codes', u'Related to'),
        }
    },
    'CreativeWork': {
        'parent': 'Thing',
        'title': u'Creative work',
        'properties': {
            'relatedTo': (u'Related works', u'Related to'),
        }
    },
    'Person': {
        'parent': 'Thing',
        'properties': {
            'relatedTo': (u'Related people', u'Related to'),
            'birthDate': (u'Births', u'Birth date'),
            'deathDate': (u'Deaths', u'Death date'),
        }
    },
    'ScholarlyArticle': {
        'parent': 'Article',
        'title': u'Scholary article',
        'properties': {
            'relatedTo': (u'Related scholary articles', u'Related to'),
        }
    },
    'SoftwareApplication': {
        'parent': 'CreativeWork',
        'properties': {
            'relatedTo': (u'Related softwares', u'Related to'),
            'operatingSystem': (u'Related operating systems', u'Related to'),
        }
    },
    'Thing': {
        'parent': None,
        'properties': {
            'relatedTo': (u'Related things', u'Related to'),
        }
    },
    'WebApplication': {
        'parent': 'SoftwareApplication',
        'properties': {
            'relatedTo': (u'Related sites', u'Related to'),
        }
    },
}


def humane_item(itemtype):
    try:
        return SUPPORTED_SCHEMA[itemtype]['title']
    except KeyError:
        return itemtype


def humane_property(itemtype, prop, inlink):
    try:
        return SUPPORTED_SCHEMA[itemtype]['properties'][prop][0 if inlink else 1]
    except KeyError:
        return prop


def get_itemtype_path(itemtype):
    try:
        parts = []
        parent = itemtype
        while parent is not None:
            parts.append(parent)
            parent = SUPPORTED_SCHEMA[parent]['parent']
        parts.reverse()
        parts.append('')
        return '/'.join(parts)
    except KeyError:
        raise ValueError('Unsupported schema: %s' % itemtype)
