from google.appengine.api import memcache
import threading


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


def add_recent_email(email):
    key = 'view\trecentemails'
    try:
        emails = get_recent_emails()
        if len(emails) > 0 and emails[-1] == email:
            return
        if email in emails:
            emails.remove(email)
        emails.append(email)

        value = emails[-max_recent_users:]
        memcache.set(key, value)
        prc.set(key, value)
    except:
        return None


def get_recent_emails():
    key = 'view\trecentemails'
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def get_recent_emails():
    key = 'view\trecentemails'
    if prc.get(key) is None:
        try:
            emails = memcache.get(key)
            if emails is None:
                memcache.flush_all()
                prc.flush_all()
                prc.set(key, [])
            else:
                prc.set(key, emails)
        except:
            pass

    return prc.get(key)


def set_titles(email, content):
    try:
        add_recent_email(email)
        memcache.set('model\ttitles\t%s' % email, content)
    except:
        return None


def get_titles(email):
    try:
        return memcache.get('model\ttitles\t%s' % email)
    except:
        return None


def del_titles():
    try:
        emails = get_recent_emails()
        keys = ['model\ttitles\t%s' % email
                for email in emails + ['None']]
        memcache.delete_multi(keys)
    except:
        return None


def set_config(value):
    key = 'model\tconfig'
    try:
        memcache.set(key, value)
        prc.set(key, value)
    except:
        return None


def set_rendered_body(title, value):
    key = 'model\trendered_body\t%s' % title
    try:
        memcache.set(key, value)
        prc.set(key, value)
    except:
        return None


def set_wikiquery(q, email, value):
    key = 'model\twikiquery\t%s\t%s' % (q, email)
    try:
        memcache.set(key, value, 60 * 10)
        prc.set(key, value)
    except:
        return None


def set_data(title, value):
    key = 'model\tdata\t%s' % title
    try:
        memcache.set(key, value)
        prc.set(key, value)
    except:
        return None


def set_metadata(title, value):
    key = 'model\tmetadata\t%s' % title
    try:
        memcache.set(key, value)
        prc.set(key, value)
    except:
        return None


def set_hashbangs(title, value):
    key = 'model\thashbangs\t%s' % title
    try:
        memcache.set(key, value)
        prc.set(key, value)
    except:
        return None


def get_config():
    key = 'model\tconfig'
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def get_rendered_body(title):
    key = 'model\trendered_body\t%s' % title
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def get_wikiquery(q, email):
    key = 'model\twikiquery\t%s\t%s' % (q, email)
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def get_data(title):
    key = 'model\tdata\t%s' % title
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def get_metadata(title):
    key = 'model\tmetadata\t%s' % title
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def get_hashbangs(title):
    key = 'model\thashbangs\t%s' % title
    if prc.get(key) is None:
        try:
            prc.set(key, memcache.get(key))
        except:
            pass
    return prc.get(key)


def del_config():
    key = 'model\tconfig'
    try:
        memcache.delete(key)
        prc.set(key, None)
    except:
        return None


def del_rendered_body(title):
    key = 'model\trendered_body\t%s' % title
    try:
        memcache.delete(key)
        prc.set(key, None)
    except:
        return None


def del_data(title):
    key = 'model\tdata\t%s' % title
    try:
        memcache.delete(key)
        prc.set(key, None)
    except:
        return None


def del_metadata(title):
    key = 'model\tmetadata\t%s' % title
    try:
        memcache.delete(key)
        prc.set(key, None)
    except:
        return None


def del_hashbangs(title):
    key = 'model\thashbangs\t%s' % title
    try:
        memcache.delete(key)
        prc.set(key, None)
    except:
        return None
