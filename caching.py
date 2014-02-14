# -*- coding: utf-8 -*-
import threading
from google.appengine.api import memcache


c = memcache.Client()


prc = None
max_recent_users = 20


class PerRequestCache(threading.local):
    def get(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        else:
            return None

    def set(self, key, value):
        self.__dict__[key] = value

    def flush_all(self):
        self.__dict__.clear()


def create_prc():
    global prc
    prc = PerRequestCache()


if prc is None:
    create_prc()


def flush_all():
    prc.flush_all()
    c.flush_all()


def add_recent_email(email):
    emails = get_recent_emails()
    if len(emails) > 0 and emails[-1] == email:
        return
    if email in emails:
        emails.remove(email)
    emails.append(email)
    value = emails[-max_recent_users:]
    _set_cache('view\trecentemails', value)


def get_recent_emails():
    key = 'view\trecentemails'
    try:
        emails = c.get(key)
        if emails is None:
            c.flush_all()
            emails = []
        return emails
    except:
        return []


def set_titles(email, content):
    try:
        add_recent_email(email)
        c.set('model\ttitles\t%s' % email, content)
    except:
        pass


def get_titles(email):
    try:
        return c.get('model\ttitles\t%s' % email)
    except:
        pass


def del_titles():
    try:
        emails = get_recent_emails()
        keys = ['model\ttitles\t%s' % email
                for email in emails + ['None']]
        c.delete_multi(keys)
    except:
        pass


def set_schema_set(value):
    _set_cache('schema_set', value)


def set_schema(key, value):
    _set_cache('schema\t%s' % key, value)


def set_schema_itemtypes(value):
    _set_cache('schema\titemtypes', value)


def set_schema_property(prop_name, prop):
    _set_cache('schema\tprop\t%s' % prop_name, prop)


def set_schema_datatype(type_name, prop):
    _set_cache('schema\tdatatype\t%s' % type_name, prop)

def set_cardinalities(key, data):
    try:
        return c.set('schema\tcardinalities\t%s' % key, data)
    except:
        pass

def set_config(value):
    _set_cache('model\tconfig', value)


def set_rendered_body(title, value):
    if not value:
        return

    _set_cache('model\trendered_body\t%s' % title, value)


def set_wikiquery(q, email, value):
    # adaptive expiration time
    exp_sec = 60
    if type(value) == list:
        if len(value) < 2:
            exp_sec = 60
        elif len(value) < 10:
            exp_sec = 60 * 5
        elif len(value) < 100:
            exp_sec = 60 * 60
        elif len(value) < 500:
            exp_sec = 60 * 60 * 24

    _set_cache('model\twikiquery\t%s\t%s' % (q, email), value, exp_sec)


def set_data(title, value):
    _set_cache('model\tdata\t%s' % title, value)


def set_metadata(title, value):
    _set_cache('model\tmetadata\t%s' % title, value)


def set_hashbangs(title, value):
    _set_cache('model\thashbangs\t%s' % title, value)




def get_schema_set():
    return _get_cache('schema_set')


def get_schema(key):
    return _get_cache('schema\t%s' % key)


def get_schema_itemtypes():
    return _get_cache('schema\titemtypes')


def get_schema_property(prop_name):
    return _get_cache('schema\tprop\t%s' % prop_name)


def get_schema_datatype(type_name):
    return _get_cache('schema\tdatatype\t%s' % type_name)

def get_cardinalities(key):
    try:
        return c.get('schema\tcardinalities\t%s' % key)
    except:
        pass

def get_config():
    return _get_cache('model\tconfig')


def get_rendered_body(title):
    return _get_cache('model\trendered_body\t%s' % title)


def get_wikiquery(q, email):
    return _get_cache('model\twikiquery\t%s\t%s' % (q, email))


def get_data(title):
    return _get_cache('model\tdata\t%s' % title)


def get_metadata(title):
    return _get_cache('model\tmetadata\t%s' % title)


def get_hashbangs(title):
    return _get_cache('model\thashbangs\t%s' % title)


def del_config():
    _del_cache('model\tconfig')


def del_rendered_body(title):
    _del_cache('model\trendered_body\t%s' % title)


def del_data(title):
    _del_cache('model\tdata\t%s' % title)


def del_metadata(title):
    _del_cache('model\tmetadata\t%s' % title)


def del_hashbangs(title):
    _del_cache('model\thashbangs\t%s' % title)


def _set_cache(key, value, exp_sec=0):
    try:
        prc.set(key, value)
        c.set(key, value, exp_sec)
    except:
        pass


def _get_cache(key):
    if prc.get(key) is None:
        try:
            prc.set(key, c.get(key))
        except:
            pass
    return prc.get(key)


def _del_cache(key):
    try:
        prc.set(key, None)
        c.delete(key)
    except:
        pass
