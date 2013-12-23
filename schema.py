import os
import json
import cache


SCHEMA_FILE_TO_LOAD = [
    'schema.json',
    'schema.supplement.json',
    'schema-custom.json',
]


def get_schema_set():
    schema_set = cache.get_schema_set()
    if schema_set is None:
        for schema_file in SCHEMA_FILE_TO_LOAD:
            fullpath = os.path.join(os.path.dirname(__file__), schema_file)
            try:
                with open(fullpath) as f:
                    addon = json.load(f)
                    # assign if it's the first one
                    if schema_set is None:
                        schema_set = addon
                        continue

                    # else, perform merge for properties...
                    for k, v in addon['properties'].items():
                        if k not in schema_set['properties']:
                            schema_set['properties'][k] = {}
                        for key_to_add, value_to_add in v.items():
                            schema_set['properties'][k][key_to_add] = value_to_add

                    # ...and types
                    for k, v in addon['types'].items():
                        if k not in schema_set['types']:
                            schema_set['types'][k] = {}

                            # modify supertype-subtype relationships
                            for supertype in v['supertypes']:
                                schema_set['types'][supertype]['subtypes'].append(k)

                                # inherit properties of supertypes
                                if 'properties' not in v:
                                    v['properties'] = []
                                v['properties'] += schema_set['types'][supertype]['properties']
                        for key_to_add, value_to_add in v.items():
                            schema_set['types'][k][key_to_add] = value_to_add
            except IOError:
                pass
        cache.set_schema_set(schema_set)

    return schema_set


def get_schema(itemtype):
    schema = cache.get_schema(itemtype)
    if schema is None:
        schema = get_schema_set()['types'][itemtype]
        if 'plural_label' not in schema:
            schema['plural_label'] = u'%ss' % schema['label']
        cache.set_schema(itemtype, schema)
    return schema


def get_property(prop_name):
    prop = cache.get_schema_property(prop_name)
    if prop is None:
        prop = get_schema_set()['properties'][prop_name]
        if 'reversed_label' not in prop:
            prop['reversed_label'] = '[%%s] %s' % prop['label']
        cache.set_schema_property(prop_name, prop)
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
