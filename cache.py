from google.appengine.api import memcache


max_recent_users = 20


def add_recent_email(email):
    try:
        emails = get_recent_emails()
        if len(emails) > 0 and emails[-1] == email:
            return
        if email in emails:
            emails.remove(email)
        emails.append(email)

        memcache.set('view\trecent_emails',
                     '\t'.join(emails[-max_recent_users:]))
    except:
        return None


def get_recent_emails():
    try:
        emails = memcache.get('view\trecent_emails')
        if emails is None:
            memcache.flush_all()
            return []
        else:
            return emails.split('\t')
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


def set_yaml(title, content):
    try:
        memcache.set('model\tyaml\t%s' % title, content,
                     time=60*60*24*7)
    except:
        return None


def set_rendered_body(title, content):
    try:
        memcache.set('model\trendered_body\t%s' % title, content,
                     time=60*60*24*7)
    except:
        return None


def set_hashbangs(title, content):
    try:
        memcache.set('model\thashbangs\t%s' % title, content,
                     time=60*60*24*7)
    except:
        return None


def get_yaml(title):
    try:
        return memcache.get('model\tyaml\t%s' % title)
    except:
        return None


def get_rendered_body(title):
    try:
        return memcache.get('model\trendered_body\t%s' % title)
    except:
        return None


def get_hashbangs(title):
    try:
        return memcache.get('model\thashbangs\t%s' % title)
    except:
        return None


def del_yaml(title):
    try:
        memcache.delete('model\tyaml\t%s' % title)
    except:
        return None


def del_rendered_body(title):
    try:
        memcache.delete('model\trendered_body\t%s' % title)
    except:
        return None


def del_hashbangs(title):
    try:
        memcache.delete('model\thashbangs\t%s' % title)
    except:
        return None
