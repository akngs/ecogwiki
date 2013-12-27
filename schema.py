# -*- coding: utf-8 -*-
import os
import json
import caching
import urllib2


SCHEMA_FILE_TO_LOAD = [
    'schema.json',
    'schema.supplement.json',
    'schema-custom.json',
]


def get_schema_set():
    schema_set = caching.get_schema_set()
    if schema_set is not None:
        return schema_set

    for schema_file in SCHEMA_FILE_TO_LOAD:
        fullpath = os.path.join(os.path.dirname(__file__), schema_file)
        try:
            with open(fullpath) as f:
                schema_set = _merge_schema_set(json.load(f), schema_set)
        except IOError:
            pass

    caching.set_schema_set(schema_set)
    return schema_set


def get_schema(itemtype):
    schema = caching.get_schema(itemtype)
    if schema is not None:
        return schema

    schema = get_schema_set()['types'][itemtype]
    if 'plural_label' not in schema:
        if schema['label'][-2:] in ['ay', 'ey', 'iy', 'oy', 'uy', 'wy']:
            schema['plural_label'] = u'%ss' % schema['label']
        elif schema['label'].endswith('y'):
            schema['plural_label'] = u'%sies' % schema['label'][:-1]
        elif schema['label'].endswith('s') or schema['label'].endswith('o'):
            schema['plural_label'] = u'%ses' % schema['label']
        else:
            schema['plural_label'] = u'%ss' % schema['label']
    caching.set_schema(itemtype, schema)
    return schema


def get_property(prop_name):
    prop = caching.get_schema_property(prop_name)
    if prop is not None:
        return prop

    prop = get_schema_set()['properties'][prop_name]
    if 'reversed_label' not in prop:
        prop['reversed_label'] = '[%%s] %s' % prop['label']
    caching.set_schema_property(prop_name, prop)
    return prop


def humane_item(itemtype, plural=False):
    try:
        if plural:
            return get_schema(itemtype)['plural_label']
        else:
            return get_schema(itemtype)['label']
    except KeyError:
        return itemtype


def humane_property(itemtype, prop, rev=False):
    try:
        if rev:
            propstr = get_property(prop)['reversed_label']
            if propstr.find('%s') == -1:
                return propstr
            else:
                return propstr % humane_item(itemtype, True)
        else:
            return get_property(prop)['label']
    except KeyError:
        return prop.capitalize()


def get_itemtype_path(itemtype):
    try:
        parts = []
        parent = itemtype
        while parent is not None:
            parts.append(parent)
            supers = get_schema(parent)['supertypes']
            parent = supers[0] if len(supers) > 0 else None
        parts.reverse()
        parts.append('')
        return '/'.join(parts)
    except KeyError:
        raise ValueError('Unsupported schema: %s' % itemtype)


def _merge_schema_set(addon, schema_set):
    if schema_set is None:
        return addon

    # perform merge for properties...
    for prop_key, prop_value in addon['properties'].items():
        props = schema_set['properties']
        if prop_key not in props:
            props[prop_key] = {}
        for key_to_add, value_to_add in prop_value.items():
            props[prop_key][key_to_add] = value_to_add

    # ...and types
    for type_key, type_value in addon['types'].items():
        types = schema_set['types']
        if type_key not in types:
            types[type_key] = {}

            # modify supertype-subtype relationships
            for supertype in type_value['supertypes']:
                types[supertype]['subtypes'].append(type_key)

                # inherit properties of supertypes
                if 'properties' not in type_value:
                    type_value['properties'] = []
                type_value['properties'] += types[supertype]['properties']

        for key_to_add, value_to_add in type_value.items():
            types[type_key][key_to_add] = value_to_add

    return schema_set


def to_html(o, key=None):
    obj_type = type(o)
    if isinstance(o, dict):
        return render_dict(o)
    elif obj_type == list:
        return render_list(o)
    elif obj_type == str or obj_type == unicode:
        if key is not None and key == 'schema':
            return o
        else:
            return '<a href="/%s">%s</a>' % (urllib2.quote(o.replace(u' ', u'_').encode('utf-8')), o)
    else:
        return str(o)


def render_dict(o):
    if len(o) == 1:
        return schema_to_html(o.values()[0])
    else:
        html = ['<dl class="wq wq-dict">']
        for key, value in o.items():
            html.append('<dt class="wq-key-%s">' % key)
            html.append(key)
            html.append('</dt>')
            html.append('<dd class="wq-value-%s">' % key)
            html.append(schema_to_html(value, key))
            html.append('</dd>')
        html.append('</dl>')

        return '\n'.join(html)


def render_list(o):
    html = ['<ul class="wq wq-list">']
    for value in o:
        html.append('<li>')
        html.append(schema_to_html(value))
        html.append('</li>')
    html.append('</ul>')

    return '\n'.join(html)
