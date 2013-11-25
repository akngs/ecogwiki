from google.appengine.api import memcache
import threading


max_recent_users = 20


class PerRequestCache(threading.local):
    config = None


prc = PerRequestCache()


def add_recent_email(email):
    try:
        emails = get_recent_emails()
        if len(emails) > 0 and emails[-1] == email:
            return
        if email in emails:
            emails.remove(email)
        emails.append(email)

        memcache.set('view\trecentemails', emails[-max_recent_users:])
    except:
        return None


def get_recent_emails():
    try:
        emails = memcache.get('view\trecentemails')
        if emails is None:
            memcache.flush_all()
            return []
        else:
            return emails
    except:
        return []


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
        memcache.set('model\tconfig', content, time=60*60*24*7)
        prc.config = content
    except:
        return None


def set_rendered_body(title, content):
    try:
        memcache.set('model\trendered_body\t%s' % title, content, time=60*60*24*7)
    except:
        return None


def set_metadata(title, md):
    try:
        memcache.set('model\tmetadata\t%s' % title, md, time=60*60*24*7)
    except:
        return None


def set_hashbangs(title, content):
    try:
        memcache.set('model\thashbangs\t%s' % title, content, time=60*60*24*7)
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
    try:
        return memcache.get('model\trendered_body\t%s' % title)
    except:
        return None


def get_metadata(title):
    try:
        return memcache.get('model\tmetadata\t%s' % title)
    except:
        return None


def get_hashbangs(title):
    try:
        return memcache.get('model\thashbangs\t%s' % title)
    except:
        return None


def del_config():
    try:
        memcache.delete('model\tconfig')
        PerRequestCache().config = None
    except:
        return None


def del_rendered_body(title):
    try:
        memcache.delete('model\trendered_body\t%s' % title)
    except:
        return None


def del_metadata(title):
    try:
        memcache.delete('model\tmetadata\t%s' % title)
    except:
        return None


def del_hashbangs(title):
    try:
        memcache.delete('model\thashbangs\t%s' % title)
    except:
        return None
