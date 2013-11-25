from google.appengine.api import memcache
import threading


max_recent_users = 20


class PerRequestCache(threading.local):
    config = None
    data = {}

    def get(self, key):
        if key in self.data:
            return self.data[key]
        else:
            return None

    def set(self, key, value):
        self.data[key] = value

    def flush_all(self):
        self.config = None
        self.data = {}


prc = PerRequestCache()


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


def set_config(content):
    try:
        memcache.set('model\tconfig', content)
        prc.config = content
    except:
        return None


def set_rendered_body(title, value):
    key = 'model\trendered_body\t%s' % title
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
    if prc.config is None:
        try:
            prc.config = memcache.get('model\tconfig')
        except:
            pass
    return prc.config


def get_rendered_body(title):
    key = 'model\trendered_body\t%s' % title
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
    try:
        memcache.delete('model\tconfig')
        prc.config = None
    except:
        return None


def del_rendered_body(title):
    key = 'model\trendered_body\t%s' % title
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
