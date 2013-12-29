# -*- coding: utf-8 -*-
import os
import re
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


def get_datatype(type_name):
    datatype = caching.get_schema_datatype(type_name)
    if datatype is not None:
        return datatype

    datatype = get_schema_set()['datatypes'][type_name]
    caching.set_schema_datatype(type_name, datatype)
    return datatype


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
    if 'properties' in addon:
        for prop_key, prop_value in addon['properties'].items():
            props = schema_set['properties']
            if prop_key not in props:
                props[prop_key] = {}
            for key_to_add, value_to_add in prop_value.items():
                props[prop_key][key_to_add] = value_to_add

    # ...and datatypes...
    if 'datatypes' in addon:
        for dtype_key, dtype_value in addon['datatypes'].items():
            dtypes = schema_set['datatypes']
            if dtype_key not in dtypes:
                dtypes[dtype_key] = {}

            for key_to_add, value_to_add in dtype_value.items():
                dtypes[dtype_key][key_to_add] = value_to_add

    # ...and types
    if 'types' in addon:
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
        return to_html(o.values()[0])
    else:
        html = ['<dl class="wq wq-dict">']
        for key, value in o.items():
            html.append('<dt class="wq-key-%s">' % key)
            html.append(key)
            html.append('</dt>')
            html.append('<dd class="wq-value-%s">' % key)
            html.append(to_html(value, key))
            html.append('</dd>')
        html.append('</dl>')

        return '\n'.join(html)


def render_list(o):
    html = ['<ul class="wq wq-list">']
    for value in o:
        html.append('<li>')
        html.append(to_html(value))
        html.append('</li>')
    html.append('</ul>')

    return '\n'.join(html)


class SchemaConverter(object):
    @staticmethod
    def convert(itemtype, data):
        converter = SchemaConverter(itemtype, data)
        return converter.convert_schema()

    def __init__(self, itemtype, data):
        self._itemtype = itemtype
        self._data = data

    def convert_schema(self):
        try:
            schema_item = get_schema(self._itemtype)
        except KeyError:
            raise ValueError('Unknown itemtype: %s' % self._itemtype)

        props = set(self._data.keys()).difference({'schema'})
        unknown_props = props.difference(schema_item['properties'] + schema_item['specific_properties'])
        if len(unknown_props) > 0:
            raise ValueError('Unknown properties: %s' % ','.join(unknown_props))

        return dict((prop, self.convert_prop(prop, self._data[prop])) for prop in props)

    def convert_prop(self, key, value):
        if type(value) is list:
            return [self._convert_prop(key, v) for v in value]
        else:
            return self._convert_prop(key, value)

    def _convert_prop(self, key, value):
        type_names = get_property(key)['ranges']
        for t in type_names:
            try:
                if t == 'Boolean':
                    return BooleanProperty(t, value)
                elif t == 'Date':
                    return DateProperty(t, value)
                elif t == 'DateTime':
                    return DateTimeProperty(t, value)
                elif t == 'Number':
                    return NumberProperty(t, value)
                elif t == 'Float':
                    return FloatProperty(t, value)
                elif t == 'Integer':
                    return IntegerProperty(t, value)
                elif t == 'Text':
                    return TextProperty(t, value)
                elif t == 'URL':
                    return URLProperty(t, value)
                elif t == 'Time':
                    return TimeProperty(t, value)
                elif t == 'ISBN':
                    return IsbnProperty(t, value)
                else:
                    return ThingProperty(t, value)
            except ValueError:
                pass
        raise ValueError()


class Property(object):
    def __init__(self, t, value):
        pass

    def __eq__(self, o):
        if type(o) != type(self):
            return False
        return True

    def is_wikilink(self):
        return False


class ThingProperty(Property):
    def __init__(self, t, value):
        super(ThingProperty, self).__init__(t, value)
        try:
            self.itemtype = t
            self.schema = get_schema(t)
        except KeyError:
            raise ValueError('Unknown itemtype: %s' % t)
        self.value = value

    def __eq__(self, o):
        if not super(ThingProperty, self).__eq__(o):
            return False
        if o.itemtype != self.itemtype:
            return False
        if o.value != self.value:
            return False
        return True

    def is_wikilink(self):
        return True


class TypeProperty(Property):
    def __init__(self, t, value):
        super(TypeProperty, self).__init__(t, value)
        if t not in get_schema_set()['datatypes']:
            raise ValueError('Unknown datatype: %s' % t)
        self.datatype = t

    def __eq__(self, o):
        if not super(TypeProperty, self).__eq__(o):
            return False
        if o.datatype != self.datatype:
            return False


class BooleanProperty(TypeProperty):
    def __init__(self, t, value):
        super(BooleanProperty, self).__init__(t, value)
        if value.lower() in ('1', 'yes', 'true'):
            self.value = True
        elif value.lower() in ('0', 'no', 'false'):
            self.value = False
        else:
            raise ValueError('Invalid boolean: %s' % value)

    def __eq__(self, o):
        if not super(BooleanProperty, self).__eq__(o):
            return False
        if o.value != self.value:
            return False


class TextProperty(TypeProperty):
    def __init__(self, t, value):
        super(TextProperty, self).__init__(t, value)
        self.value = value

    def __eq__(self, o):
        if not super(TextProperty, self).__eq__(o):
            return False
        if o.value != self.value:
            return False


class NumberProperty(TypeProperty):
    def __init__(self, t, value):
        super(NumberProperty, self).__init__(t, value)
        try:
            if value.find('.') == -1:
                self.value = int(value)
            else:
                self.value = float(value)
        except ValueError:
            raise ValueError('Invalid number: %s' % value)

    def __eq__(self, o):
        if not super(NumberProperty, self).__eq__(o):
            return False
        if o.value != self.value:
            return False


class IntegerProperty(NumberProperty):
    def __init__(self, t, value):
        super(IntegerProperty, self).__init__(t, value)

        try:
            self.value = int(value)
        except ValueError:
            raise ValueError('Invalid integer: %s' % value)
        if self.value != float(value):
            raise ValueError('Invalid integer: %s' % value)


class FloatProperty(NumberProperty):
    def __init__(self, t, value):
        super(FloatProperty, self).__init__(t, value)

        try:
            self.value = float(value)
        except ValueError:
            raise ValueError('Invalid float: %s' % value)


class DateTimeProperty(TextProperty):
    # TODO implement this (shouldn't inherit from TextProperty)
    pass


class TimeProperty(TextProperty):
    # TODO implement this (shouldn't inherit from TextProperty)
    pass


class URLProperty(TypeProperty):
    P_URL = ur'\w+://[a-zA-Z0-9\~\!\@\#\$\%\^\&\*\-\_\=\+\[\]\\\:\;\"\'\,\.\'\?/]+'

    def __init__(self, t, value):
        super(URLProperty, self).__init__(t, value)
        m = re.match(URLProperty.P_URL, value)
        if m is None:
            raise ValueError('Invalid URL: %s' % value)
        self.value = value

    def __eq__(self, o):
        if not super(URLProperty, self).__eq__(o):
            return False
        if o.value != self.value:
            return False


class DateProperty(TypeProperty):
    P_DATE = ur'(?P<y>\d+)(-(?P<m>(\d\d|\?\?))-(?P<d>(\d\d|\?\?)))?( (?P<bce>BCE))?'

    def __init__(self, t, value):
        super(DateProperty, self).__init__(t, value)
        m = re.match(DateProperty.P_DATE, value)

        if m is None:
            raise ValueError('Invalid value: %s' % value)
        self.year = int(m.group('y'))

        self.month = int(m.group('m')) if m.group('m') else None
        if self.month is not None and self.month > 12:
            raise ValueError('Invalid month: %d' % self.month)

        self.day = int(m.group('d')) if m.group('d') else None
        if self.day is not None and self.day > 31:
            raise ValueError('Invalid day: %d' % self.day)

        self.bce = m.group('bce') == 'BCE'

    def __eq__(self, o):
        if not super(DateProperty, self).__eq__(o):
            return False
        if o.year != self.year:
            return False
        if o.month != self.month:
            return False
        if o.day != self.day:
            return False
        if o.bce != self.bce:
            return False
        return True

    def is_year_only(self):
        return self.month is None and self.day is None

    def is_wikilink(self):
        return True


class IsbnProperty(TypeProperty):
    P_ISBN = ur'[\dxX]{10,13}'

    def __init__(self, t, value):
        super(IsbnProperty, self).__init__(t, value)
        m = re.match(IsbnProperty.P_ISBN, value)
        if m is None:
            raise ValueError('Invalid ISBN: %s' % value)
        self.value = value

        if self.value[:2] == '89':
            self.link = u'http://www.aladin.co.kr/shop/wproduct.aspx?ISBN=978%s' % self.value
        elif self.value[:5] == '97889':
            self.link = u'http://www.aladin.co.kr/shop/wproduct.aspx?ISBN=%s' % self.value
        else:
            self.link = u'http://www.amazon.com/gp/product/%s' % self.value

    def __eq__(self, o):
        if not super(IsbnProperty, self).__eq__(o):
            return False
        if o.value != self.value:
            return False
