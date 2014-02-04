# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import caching
import operator
from datetime import date
from markdownext import md_wikilink


SCHEMA_TO_LOAD = [
    'schema.json',
    'schema.supplement.json',
    'schema-custom.json',
]


def get_schema_set():
    schema_set = caching.get_schema_set()
    if schema_set is not None:
        return schema_set

    for s in SCHEMA_TO_LOAD:
        if type(s) == dict:
            new_schema = s
        else:
            fullpath = os.path.join(os.path.dirname(__file__), s)
            try:
                with open(fullpath) as f:
                    new_schema = json.load(f)
            except IOError:
                new_schema = {}

        schema_set = _merge_schema_set(new_schema, schema_set)

    caching.set_schema_set(schema_set)
    return schema_set


def get_legacy_spellings():
    schema_set = get_schema_set()
    props = schema_set['properties']
    return {pname for pname, pdata in props.items() if 'comment' in pdata and pdata['comment'].find('(legacy spelling;') != -1}


def get_sc_schema(itemtype):
    schema = get_schema(itemtype).copy()

    # extend properties to include cardinalities and type infos
    props = {}
    for p in schema['properties']:
        props[p] = {
            'cardinality': get_cardinality(itemtype, p),
            'type': get_property(p)
        }
    schema['properties'] = props

    # remove specific properties which are redundent
    del schema['specific_properties']

    return schema


def get_schema(itemtype, self_contained=False):
    if self_contained:
        return get_sc_schema(itemtype)

    item = caching.get_schema(itemtype)
    if item is not None:
        return item

    item = get_schema_set()['types'][itemtype]

    # populate missing fields
    if 'url' not in item:
        item['url'] = '/sp.schema/types/%s' % itemtype
    if 'id' not in item:
        item['id'] = itemtype
    if 'label' not in item:
        item['label'] = item['id']
    if 'comment' not in item:
        item['comment'] = item['label']
    if 'comment_plain' not in item:
        item['comment_plain'] = item['comment']
    if 'subtypes' not in item:
        item['subtypes'] = []
    if 'ancestors' not in item:
        # collect ancestors
        ancestors = []
        parent = item
        while len(parent['supertypes']) > 0:
            parent_itemtype = parent['supertypes'][0]
            ancestors.append(parent_itemtype)
            parent = get_schema(parent_itemtype)
        ancestors.reverse()
        item['ancestors'] = ancestors
    if 'plural_label' not in item:
        if item['label'][-2:] in ['ay', 'ey', 'iy', 'oy', 'uy', 'wy']:
            item['plural_label'] = u'%ss' % item['label']
        elif item['label'].endswith('y'):
            item['plural_label'] = u'%sies' % item['label'][:-1]
        elif item['label'].endswith('s') or item['label'].endswith('o'):
            item['plural_label'] = u'%ses' % item['label']
        else:
            item['plural_label'] = u'%ss' % item['label']

    # inherit properties of supertypes
    if 'properties' not in item:
        item['properties'] = []

    for stype in item['supertypes']:
        item['properties'] += get_schema(stype)['properties']
    item['properties'] = list(set(item['properties']))

    # remove legacy spellings
    legacy_spellings = get_legacy_spellings()
    props = set(item['properties']).difference(legacy_spellings)
    sprops = set(item['specific_properties']).difference(legacy_spellings)

    # merge specific_properties into properties
    item['properties'] = sorted(list(props.union(sprops)))
    item['specific_properties'] = sorted(list(sprops))

    caching.set_schema(itemtype, item)
    return item


def get_itemtypes():
    itemtypes = caching.get_schema_itemtypes()
    if itemtypes is not None:
        return itemtypes

    itemtypes = sorted(get_schema_set()['types'].keys())
    caching.set_schema_itemtypes(itemtypes)
    return itemtypes


def get_datatype(type_name):
    dtype = caching.get_schema_datatype(type_name)
    if dtype is not None:
        return dtype

    dtype = get_schema_set()['datatypes'][type_name]

    # populate missing fields
    if 'url' not in dtype:
        dtype['url'] = '/sp.schema/datatypes/%s' % type_name
    if 'properties' not in dtype:
        dtype['properties'] = []
    if 'specific_properties' not in dtype:
        dtype['specific_properties'] = []
    if 'supertypes' not in dtype:
        dtype['supertypes'] = ['DataType']
    if 'subtypes' not in dtype:
        dtype['subtypes'] = []
    if 'id' not in dtype:
        dtype['id'] = type_name
    if 'label' not in dtype:
        dtype['label'] = dtype['id']
    if 'comment' not in dtype:
        dtype['comment'] = dtype['label']
    if 'comment_plain' not in dtype:
        dtype['comment_plain'] = dtype['comment']
    if 'ancestors' not in dtype:
        dtype['ancestors'] = dtype['supertypes']

    caching.set_schema_datatype(type_name, dtype)
    return dtype


def get_property(prop_name):
    if prop_name in get_legacy_spellings():
        raise KeyError('Legacy spelling: %s' % prop_name)

    prop = caching.get_schema_property(prop_name)
    if prop is not None:
        return prop

    prop = get_schema_set()['properties'][prop_name]

    # populate missing fields
    if 'domains' not in prop:
        prop['domains'] = ['Thing']
    if 'ranges' not in prop:
        prop['ranges'] = ['Text']
    if 'id' not in prop:
        prop['id'] = prop_name
    if 'label' not in prop:
        prop['label'] = prop['id']
    if 'comment' not in prop:
        prop['comment'] = prop['label']
    if 'comment_plain' not in prop:
        prop['comment_plain'] = prop['comment']
    if 'reversed_label' not in prop:
        prop['reversed_label'] = '[%%s] %s' % prop['label']

    caching.set_schema_property(prop_name, prop)
    return prop


def get_cardinality(itemtype, prop_name):
    try:
        item = get_schema(itemtype)
        return item['cardinalities'][prop_name]
    except KeyError:
        prop = get_property(prop_name)
        return prop['cardinality'] if 'cardinality' in prop else [0, 0]


def get_cardinalities(itemtype):
    return dict((pname, get_cardinality(itemtype, pname))
                for pname in get_schema(itemtype)['properties'])


def humane_item(itemtype, plural=False):
    try:
        if plural:
            return get_schema(itemtype)['plural_label']
        return get_schema(itemtype)['label']
    except KeyError:
        return itemtype


def humane_property(itemtype, prop, rev=False):
    try:
        if not rev:
            return get_property(prop)['label']

        propstr = get_property(prop)['reversed_label']
        if propstr.find('%s') == -1:
            return propstr
        return propstr % humane_item(itemtype, True)
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

            types[k].update(v)

    return schema_set


def to_html(o):
    obj_type = type(o)
    if isinstance(o, dict):
        return render_dict(o)
    elif obj_type == list:
        return render_list(o)
    elif isinstance(o, Property):
        return o.render()
    return unicode(o)


def render_dict(o):
    if len(o) == 1:
        return to_html(o.values()[0])

    html = [u'<dl class="wq wq-dict">']
    for key, value in o.items():
        html.append(u'<dt class="wq-key-%s">%s</dt>' % (key, key))
        html.append(u'<dd class="wq-value-%s">%s</dd>' % (key, to_html(value)))
    html.append(u'</dl>')

    return '\n'.join(html)


def render_list(o):
    return '\n'.join(
        [u'<ul class="wq wq-list">'] +
        [u'<li>%s</li>' % to_html(value) for value in o] +
        [u'</ul>']
    )


class SchemaConverter(object):
    def __init__(self, itemtype, data):
        self._itemtype = itemtype
        self._data = data.copy()

    def convert_schema(self):
        try:
            schema_item = get_schema(self._itemtype)
        except KeyError:
            raise ValueError('Unknown itemtype: %s' % self._itemtype)

        props = set(self._data.keys())
        unknown_props = props.difference(schema_item['properties'] + schema_item['specific_properties'] + ['schema'])
        known_props = props.difference(unknown_props)

        self.check_cardinality()

        knowns = [(p, SchemaConverter.convert_prop(self._itemtype, p, self._data[p])) for p in known_props]
        unknowns = [(p, InvalidProperty(self._itemtype, p, p, self._data[p])) for p in unknown_props]
        return dict(knowns + unknowns)

    def check_cardinality(self):
        cardinalities = get_cardinalities(self._itemtype)
        for pname, (cfrom, cto) in cardinalities.items():
            if pname not in self._data:
                num = 0
            elif type(self._data[pname]) == list:
                num = len(self._data[pname])
            else:
                num = 1

            if cfrom > num:
                raise ValueError('There should be at least %d [%s] item(s).' % (cfrom, pname))
            elif cto == 1 and cto < num:
                self._data[pname] = self._data[pname][0]
            elif cto != 0 and cto < num:
                self._data[pname] = self._data[pname][:cto]

    @classmethod
    def convert_prop(cls, itemtype, pname, pvalue):
        if type(pvalue) is list:
            return [cls._convert_prop(itemtype, pname, pv) for pv in pvalue]
        else:
            return cls._convert_prop(itemtype, pname, pvalue)

    @staticmethod
    def convert(itemtype, data):
        return SchemaConverter(itemtype, data).convert_schema()

    @staticmethod
    def _convert_prop(itemtype, pname, pvalue):
        if pname == 'schema':
            return TextProperty(itemtype, 'Text', pname, pvalue)

        prop = get_property(pname)
        if 'enum' in prop and pvalue not in prop['enum']:
            return InvalidProperty(itemtype, 'Invalid', pname, pvalue)

        ranges = prop['ranges']
        types = [(SchemaConverter.type_by_name(ptype), ptype) for ptype in ranges]
        types = [(type_obj, ptype, PRIORITY[type_obj]) for type_obj, ptype in types]
        sorted_types = sorted(types, key=operator.itemgetter(2))

        for type_obj, ptype, _ in sorted_types:
            try:
                return type_obj(itemtype, ptype, pname, pvalue)
            except ValueError:
                pass
        return InvalidProperty(itemtype, 'Invalid', pname, pvalue)

    @staticmethod
    def type_by_name(name):
        try:
            return getattr(sys.modules[__name__], '%sProperty' % name)
        except AttributeError:
            return ThingProperty


class Property(object):
    def __init__(self, itemtype, ptype, pname, pvalue):
        self.itemtype = itemtype
        self.pname = pname
        self.ptype = ptype
        self.pvalue = pvalue

    def __eq__(self, o):
        return type(o) == type(self) and o.pname == self.pname and o.pvalue == self.pvalue

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
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(ThingProperty, self).__init__(itemtype, ptype, pname, pvalue)
        try:
            get_schema(ptype)
        except KeyError:
            raise ValueError('Unknown itemtype: %s' % ptype)
        self.value = pvalue

    def __eq__(self, o):
        return super(ThingProperty, self).__eq__(o) and o.value == self.value

    def is_wikilink(self):
        return True

    def render(self):
        return md_wikilink.render_wikilink(self.value)


class TypeProperty(Property):
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(TypeProperty, self).__init__(itemtype, ptype, pname, pvalue)
        if ptype not in get_schema_set()['datatypes']:
            raise ValueError('Unknown datatype: %s' % ptype)


class BooleanProperty(TypeProperty):
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(BooleanProperty, self).__init__(itemtype, ptype, pname, pvalue)
        if type(pvalue) == str or type(pvalue) == unicode:
            if pvalue.lower() in ('1', 'yes', 'true'):
                pvalue = True
            elif pvalue.lower() in ('0', 'no', 'false'):
                pvalue = False
            else:
                raise ValueError('Invalid boolean: %s' % pvalue)

        if pvalue:
            self.value = True
        else:
            self.value = False


class TextProperty(TypeProperty):
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(TextProperty, self).__init__(itemtype, ptype, pname, pvalue)
        self.value = pvalue

    def is_wikilink(self):
        return self.pname == 'name'

    def render(self):
        if self.is_wikilink():
            return md_wikilink.render_wikilink(self.pvalue)
        else:
            return super(TextProperty, self).render()


class NumberProperty(TypeProperty):
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(NumberProperty, self).__init__(itemtype, ptype, pname, pvalue)
        try:
            if pvalue.find('.') == -1:
                self.value = int(pvalue)
            else:
                self.value = float(pvalue)
        except ValueError:
            raise ValueError('Invalid number: %s' % pvalue)


class IntegerProperty(NumberProperty):
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(IntegerProperty, self).__init__(itemtype, ptype, pname, pvalue)

        try:
            self.value = int(pvalue)
        except ValueError:
            raise ValueError('Invalid integer: %s' % pvalue)
        if self.value != float(pvalue):
            raise ValueError('Invalid integer: %s' % pvalue)


class FloatProperty(NumberProperty):
    def __init__(self, itemtype, ptype, pname, pvalue):
        super(FloatProperty, self).__init__(itemtype, ptype, pname, pvalue)

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

    def __init__(self, itemtype, ptype, pname, pvalue):
        super(URLProperty, self).__init__(itemtype, ptype, pname, pvalue)
        m = re.match(URLProperty.P_URL, pvalue)
        if m is None:
            raise ValueError('Invalid URL: %s' % pvalue)
        self.value = pvalue

    def render(self):
        return u'<a href="%s" class="url" itemprop="url">%s</a>' % (self.value, self.value)


class DateProperty(TypeProperty):
    P_DATE = ur'(?P<y>\d+)(-(?P<m>(\d\d|\?\?))-(?P<d>(\d\d|\?\?)))?( (?P<bce>BCE))?'

    def __init__(self, itemtype, ptype, pname, pvalue):
        super(DateProperty, self).__init__(itemtype, ptype, pname, pvalue)
        if isinstance(pvalue, date):
            pvalue = pvalue.strftime("%Y-%m-%d")
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
        return super(DateProperty, self).__eq__(o) and o.year == self.year and o.month == self.month and o.day == self.day and o.bce == self.bce

    def is_year_only(self):
        return self.month is None and self.day is None

    def is_wikilink(self):
        return True

    def render(self):
        return md_wikilink.render_wikilink(self.pvalue)


class ISBNProperty(TypeProperty):
    P_ISBN = ur'[\dxX]{10,13}'

    def __init__(self, itemtype, ptype, pname, pvalue):
        super(ISBNProperty, self).__init__(itemtype, ptype, pname, pvalue)
        if re.match(ISBNProperty.P_ISBN, pvalue) is None:
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


PRIORITY = {
    ISBNProperty: 1,
    URLProperty: 1,

    DateProperty: 2,
    DateTimeProperty: 2,
    TimeProperty: 2,

    BooleanProperty: 3,

    IntegerProperty: 3,
    FloatProperty: 3,
    NumberProperty: 3,

    TextProperty: 4,

    TypeProperty: 5,

    ThingProperty: 6,
    InvalidProperty: 6,

    Property: 7,
}
