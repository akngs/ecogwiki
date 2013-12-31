# -*- coding: utf-8 -*-
import os
import re
import json
import caching
import urllib2
from markdownext import md_wikilink


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
        props = schema_set['properties']
        for k, v in addon['properties'].items():
            if k not in props:
                props[k] = {}
            props[k].update(v)

    # ...and datatypes...
    if 'datatypes' in addon:
        dtypes = schema_set['datatypes']
        for k, v in addon['datatypes'].items():
            if k not in dtypes:
                dtypes[k] = {}
            dtypes[k].update(v)

    # ...and types
    if 'types' in addon:
        types = schema_set['types']
        for k, v in addon['types'].items():
            if k not in types:
                types[k] = {}

                # modify supertype-subtype relationships
                for supertype in v['supertypes']:
                    types[supertype]['subtypes'].append(k)

                    # inherit properties of supertypes
                    if 'properties' not in v:
                        v['properties'] = []
                    v['properties'] += types[supertype]['properties']

            types[k].update(v)

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
    elif isinstance(o, Property):
        return o.render()
    else:
        return str(o)


def render_dict(o):
    if len(o) == 1:
        return to_html(o.values()[0])
    else:
        html = ['<dl class="wq wq-dict">']
        for key, value in o.items():
            html.append('<dt class="wq-key-%s">%s</dt>' % (key, key))
            html.append('<dd class="wq-value-%s">%s</dd>' % (key, to_html(value, key)))
        html.append('</dl>')

        return '\n'.join(html)


def render_list(o):
    return '\n'.join(
        ['<ul class="wq wq-list">'] +
        ['<li>%s</li>' % to_html(value) for value in o] +
        ['</ul>']
    )


class SchemaConverter(object):
    def __init__(self, itemtype, data):
        self._itemtype = itemtype
        self._data = data

    def convert_schema(self):
        try:
            schema_item = get_schema(self._itemtype)
        except KeyError:
            raise ValueError('Unknown itemtype: %s' % self._itemtype)

        props = set(self._data.keys())
        unknown_props = props.difference(schema_item['properties'] + schema_item['specific_properties'] + ['schema'])
        known_props = props.difference(unknown_props)

        knowns = [(p, SchemaConverter.convert_prop(self._itemtype, p, self._data[p])) for p in known_props]
        unknowns = [(p, InvalidProperty(self._itemtype, p, self._data[p])) for p in unknown_props]
        return dict(knowns + unknowns)

    @classmethod
    def convert_prop(cls, itemtype, pkey, pvalue):
        if type(pvalue) is list:
            return [cls._convert_prop(itemtype, pkey, pv) for pv in pvalue]
        else:
            return cls._convert_prop(itemtype, pkey, pvalue)

    @staticmethod
    def convert(itemtype, data):
        converter = SchemaConverter(itemtype, data)
        return converter.convert_schema()

    @staticmethod
    def _convert_prop(itemtype, pkey, pvalue):
        if pkey == 'schema':
            return TextProperty(itemtype, 'Text', pvalue)

        for ptype in get_property(pkey)['ranges']:
            try:
                if ptype == 'Boolean':
                    return BooleanProperty(itemtype, ptype, pvalue)
                elif ptype == 'Date':
                    return DateProperty(itemtype, ptype, pvalue)
                elif ptype == 'DateTime':
                    return DateTimeProperty(itemtype, ptype, pvalue)
                elif ptype == 'Number':
                    return NumberProperty(itemtype, ptype, pvalue)
                elif ptype == 'Float':
                    return FloatProperty(itemtype, ptype, pvalue)
                elif ptype == 'Integer':
                    return IntegerProperty(itemtype, ptype, pvalue)
                elif ptype == 'Text':
                    return TextProperty(itemtype, ptype, pvalue)
                elif ptype == 'URL':
                    return URLProperty(itemtype, ptype, pvalue)
                elif ptype == 'Time':
                    return TimeProperty(itemtype, ptype, pvalue)
                elif ptype == 'ISBN':
                    return IsbnProperty(itemtype, ptype, pvalue)
                else:
                    return ThingProperty(itemtype, ptype, pvalue)
            except ValueError:
                pass
        return InvalidProperty(itemtype, 'Invalid', pvalue)


class Property(object):
    def __init__(self, itemtype, ptype, pvalue):
        self.itemtype = itemtype
        self.ptype = ptype
        self.pvalue = pvalue

    def __eq__(self, o):
        if type(o) != type(self):
            return False
        if o.pvalue != self.pvalue:
            return False
        return True

    def is_wikilink(self):
        return False

    def render(self):
        return self.pvalue


class InvalidProperty(Property):
    def __eq__(self, other):
        return False

    def render(self):
        return u'<span class="error">%s</span>' % self.pvalue


class ThingProperty(Property):
    def __init__(self, itemtype, ptype, pvalue):
        super(ThingProperty, self).__init__(itemtype, ptype, pvalue)
        try:
            get_schema(ptype)
        except KeyError:
            raise ValueError('Unknown itemtype: %s' % ptype)
        self.value = pvalue

    def __eq__(self, o):
        if not super(ThingProperty, self).__eq__(o):
            return False
        if o.value != self.value:
            return False
        return True

    def is_wikilink(self):
        return True

    def render(self):
        return md_wikilink.render_wikilink(self.value)


class TypeProperty(Property):
    def __init__(self, itemtype, ptype, pvalue):
        super(TypeProperty, self).__init__(itemtype, ptype, pvalue)
        if ptype not in get_schema_set()['datatypes']:
            raise ValueError('Unknown datatype: %s' % ptype)

    def __eq__(self, o):
        if not super(TypeProperty, self).__eq__(o):
            return False
        if o.ptype != self.ptype:
            return False
        if o.pvalue != self.pvalue:
            return False
        return True


class BooleanProperty(TypeProperty):
    def __init__(self, itemtype, ptype, pvalue):
        super(BooleanProperty, self).__init__(itemtype, ptype, pvalue)
        if pvalue.lower() in ('1', 'yes', 'true'):
            self.value = True
        elif pvalue.lower() in ('0', 'no', 'false'):
            self.value = False
        else:
            raise ValueError('Invalid boolean: %s' % pvalue)


class TextProperty(TypeProperty):
    def __init__(self, itemtype, ptype, pvalue):
        super(TextProperty, self).__init__(itemtype, ptype, pvalue)
        self.value = pvalue


class NumberProperty(TypeProperty):
    def __init__(self, itemtype, ptype, pvalue):
        super(NumberProperty, self).__init__(itemtype, ptype, pvalue)
        try:
            if pvalue.find('.') == -1:
                self.value = int(pvalue)
            else:
                self.value = float(pvalue)
        except ValueError:
            raise ValueError('Invalid number: %s' % pvalue)


class IntegerProperty(NumberProperty):
    def __init__(self, itemtype, ptype, pvalue):
        super(IntegerProperty, self).__init__(itemtype, ptype, pvalue)

        try:
            self.value = int(pvalue)
        except ValueError:
            raise ValueError('Invalid integer: %s' % pvalue)
        if self.value != float(pvalue):
            raise ValueError('Invalid integer: %s' % pvalue)


class FloatProperty(NumberProperty):
    def __init__(self, itemtype, ptype, pvalue):
        super(FloatProperty, self).__init__(itemtype, ptype, pvalue)

        try:
            self.value = float(pvalue)
        except ValueError:
            raise ValueError('Invalid float: %s' % pvalue)


class DateTimeProperty(TextProperty):
    # TODO implement this (shouldn't inherit from TextProperty)
    pass


class TimeProperty(TextProperty):
    # TODO implement this (shouldn't inherit from TextProperty)
    pass


class URLProperty(TypeProperty):
    P_URL = ur'\w+://[a-zA-Z0-9\~\!\@\#\$\%\^\&\*\-\_\=\+\[\]\\\:\;\"\'\,\.\'\?/]+'

    def __init__(self, itemtype, ptype, pvalue):
        super(URLProperty, self).__init__(itemtype, ptype, pvalue)
        m = re.match(URLProperty.P_URL, pvalue)
        if m is None:
            raise ValueError('Invalid URL: %s' % pvalue)
        self.value = pvalue


class DateProperty(TypeProperty):
    P_DATE = ur'(?P<y>\d+)(-(?P<m>(\d\d|\?\?))-(?P<d>(\d\d|\?\?)))?( (?P<bce>BCE))?'

    def __init__(self, itemtype, ptype, pvalue):
        super(DateProperty, self).__init__(itemtype, ptype, pvalue)
        m = re.match(DateProperty.P_DATE, pvalue)

        if m is None:
            raise ValueError('Invalid value: %s' % pvalue)
        self.year = int(m.group('y'))

        if m.group('m') == u'??':
            self.month = None
        else:
            self.month = int(m.group('m')) if m.group('m') else None
        if self.month is not None and self.month > 12:
            raise ValueError('Invalid month: %d' % self.month)

        if m.group('d') == u'??':
            self.day = 1 if self.month is not None else None
        else:
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

    def render(self):
        return md_wikilink.render_wikilink(self.pvalue)


class IsbnProperty(TypeProperty):
    P_ISBN = ur'[\dxX]{10,13}'

    def __init__(self, itemtype, ptype, pvalue):
        super(IsbnProperty, self).__init__(itemtype, ptype, pvalue)
        if re.match(IsbnProperty.P_ISBN, pvalue) is None:
            raise ValueError('Invalid ISBN: %s' % pvalue)
        self.value = pvalue

    def render(self):
        if self.value[:2] == '89':
            url = u'http://www.aladin.co.kr/shop/wproduct.aspx?ISBN=978%s' % self.value
        elif self.value[:5] == '97889':
            url = u'http://www.aladin.co.kr/shop/wproduct.aspx?ISBN=%s' % self.value
        else:
            url = u'http://www.amazon.com/gp/product/%s' % self.value

        return u'<a href="%s" class="isbn" itemprop="isbn">%s</a>' % (url, self.value)
