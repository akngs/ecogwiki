# -*- coding: utf-8 -*-
import re
import yaml
import main
import cache
import random
import schema
import search
import hashlib
import urllib2
import markdown
import operator
from bzrlib.merge3 import Merge3
from lxml.html.clean import Cleaner
from collections import OrderedDict
from google.appengine.ext import ndb
from google.appengine.api import users
from datetime import datetime, timedelta
from markdown.extensions.def_list import DefListExtension
from markdownext import md_url, md_wikilink, md_itemprop, md_mathjax


class PageOperationMixin(object):
    re_img = re.compile(ur'<p><img( .+? )/></p>')
    re_metadata = re.compile(ur'^\.([^\s]+)(\s+(.+))?$')
    re_special_titles_years = re.compile(ur'^(10000|\d{1,4})( BCE)?$')
    re_special_titles_dates = re.compile(ur'^((?P<month>January|February|March|'
                                         ur'April|May|June|July|August|'
                                         ur'September|October|November|'
                                         ur'December)( (?P<date>[0123]?\d))?)$')

    @property
    def rendered_body(self):
        # body
        body_parts = [PageOperationMixin.remove_metadata(self.body)]

        # incoming links
        if len(self.inlinks) > 0:
            lines = [u'# Incoming Links']
            for rel, links in self.inlinks.items():
                itemtype, rel = rel.split('/')
                humane_rel = schema.humane_property(itemtype, rel, True)
                lines.append(u'## %s' % humane_rel)

                # remove dups and sort
                links = list(set(links))
                links.sort()

                lines += [u'* [[%s]]' % title for title in links]
            body_parts.append(u'\n'.join(lines))

        # related links
        related_links = self.related_links_by_score
        if len(related_links) > 0:
            lines = [u'# Suggested Pages']
            lines += [u'* {{.score::%.3f}} [[%s]]' % (score, title)
                      for title, score in related_links.items()[:10]]
            body_parts.append(u'\n'.join(lines))

        # other posts
        if self.older_title or self.newer_title:
            lines = [u'# Other Posts']
            if self.newer_title:
                lines.append(u'* {{.newer::newer}} [[%s]]' % self.newer_title)
            if self.older_title:
                lines.append(u'* {{.older::older}} [[%s]]' % self.older_title)
            body_parts.append(u'\n'.join(lines))

        # render to html
        rendered = md.convert(u'\n'.join(body_parts))

        # add table of contents
        final = TocGenerator(rendered).add_toc()

        # add class for embedded image
        final = PageOperationMixin.re_img.sub(u'<p class="img-container"><img \\1/></p>', final)

        # sanitize
        if final:
            cleaner = Cleaner(safe_attrs_only=False)
            final = cleaner.clean_html(final)

        return final

    @property
    def absolute_url(self):
        return u'/%s' % WikiPage.title_to_path(self.title)

    @property
    def absolute_newer_url(self):
        return u'/%s' % WikiPage.title_to_path(self.newer_title)

    @property
    def absolute_older_url(self):
        return u'/%s' % WikiPage.title_to_path(self.older_title)

    @property
    def metadata(self):
        return self.parse_metadata(self.body)

    def can_read(self, user, default_acl=None):
        if default_acl is None:
            default_acl = PageOperationMixin.get_default_permission()

        acl = self.acl_read.split(',') if self.acl_read is not None and len(self.acl_read) != 0 else []
        if len(acl) == 0:
            acl = default_acl['read']

        if user is not None and users.is_current_user_admin():
            return True
        elif u'all' in acl or len(acl) == 0:
            return True
        elif u'login' in acl and user is not None:
            return True
        elif user is not None and user.email() in acl:
            return True
        elif self.can_write(user, default_acl):
            return True
        else:
            return False

    def can_write(self, user, default_acl=None):
        if default_acl is None:
            default_acl = PageOperationMixin.get_default_permission()

        acl = self.acl_write.split(',') if self.acl_write is not None and len(self.acl_write) != 0 else []
        if len(acl) == 0:
            acl = default_acl['write']

        if user is not None and users.is_current_user_admin():
            return True
        elif 'all' in acl:
            return True
        elif (len(acl) == 0 or u'login' in acl) and user is not None:
            return True
        elif user is not None and user.email() in acl:
            return True
        else:
            return False

    @property
    def itemtype(self):
        if 'schema' in self.metadata:
            return self.metadata['schema']
        else:
            return u'Article'

    @property
    def itemtype_url(self):
        return 'http://schema.org/%s' % self.itemtype

    @property
    def related_links_by_score(self):
        sorted_tuples = sorted(self.related_links.iteritems(),
                               key=operator.itemgetter(1),
                               reverse=True)
        return OrderedDict(sorted_tuples)

    @property
    def related_links_by_title(self):
        sorted_tuples = sorted(self.related_links.iteritems(),
                               key=operator.itemgetter(0))
        return OrderedDict(sorted_tuples)

    @property
    def special_sections(self):
        ss = {}

        if self._check_special_titles_years():
            ss[u'years'] = self._special_titles_years()
        elif self._check_special_titles_dates():
            ss[u'dates'] = self._special_titles_dates()

        return ss

    @property
    def hashbangs(self):
        return PageOperationMixin.extract_hashbangs(self.rendered_body)

    def _check_special_titles_years(self):
        return (
            self.title != '0' and
            re.match(PageOperationMixin.re_special_titles_years, self.title)
        )

    def _check_special_titles_dates(self):
        return (
            re.match(PageOperationMixin.re_special_titles_dates, self.title)
        )

    def _special_titles_years(self):
        ss = {}

        # years: list year titles
        if self.title.endswith(' BCE'):
            cur_year = -int(self.title[:-4]) + 1
        else:
            cur_year = int(self.title)

        years = range(cur_year - 3, cur_year + 4)
        year_titles = []
        for year in years:
            if year < 1:
                year_titles.append(str(abs(year - 1)) + u' BCE')
            else:
                year_titles.append(str(year))

        ss[u'title'] = 'Years'
        ss[u'years'] = year_titles
        ss[u'cur_year'] = str(cur_year)
        return ss

    def _special_titles_dates(self):
        ss = {}

        # dates: list of dates in month
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November',
                       'December']
        m = re.match(WikiPage.re_special_titles_dates, self.title)
        month = m.group('month')
        max_date = 31
        if month == 'February':
            max_date = 29
        elif month in ('April', 'June', 'September', 'November'):
            max_date = 30
        ss[u'title'] = month
        ss[u'month'] = month
        ss[u'prev_month'] = month_names[month_names.index(month) - 1]
        ss[u'next_month'] = month_names[(month_names.index(month) + 1) %
                                        len(month_names)]
        if m.group('date'):
            ss[u'cur_date'] = int(m.group('date'), 10)

        ss[u'dates'] = range(1, max_date + 1)
        return ss

    @staticmethod
    def get_default_permission():
        try:
            return WikiPage.get_config()['service']['default_permissions']
        except KeyError:
            return main.DEFAULT_CONFIG['service']['default_permissions']

    @staticmethod
    def parse_metadata(body):
        matches = []
        for line in body.split(u'\n'):
            m = re.match(WikiPage.re_metadata, line.strip())
            if m:
                matches.append(m)
            else:
                break

        metadata = {
            'content-type': 'text/x-markdown',
        }

        for m in matches:
            key = m.group(1).strip()
            value = m.group(3)
            if value is not None:
                value = value.strip()
            metadata[key] = value

        return metadata

    @staticmethod
    def remove_metadata(body):
        rest = []
        lines = iter(body.split(u'\n'))

        for line in lines:
            m = re.match(WikiPage.re_metadata, line.strip())
            if m is None:
                rest.append(line)
                break

        rest += list(lines)
        return u'\n'.join(rest)

    @staticmethod
    def extract_hashbangs(html):
        matches = re.findall(ur'<code>#!(.+?)[\n;]', html)
        if re.match(ur'.*(\\\(.+\\\)|\$\$.+\$\$)', html, re.DOTALL):
            matches.append('mathjax')
        return matches

    def make_description(self, max_length=200):
        head = PageOperationMixin.remove_metadata(self.body)[:max_length].strip()

        # try newline
        index = head.find(u'\n')
        if index != -1:
            return head[:index].strip()

        # try period
        index = 0
        while index < max_length:
            next_index = head.find(u'. ', index)
            if next_index == -1:
                break
            index = next_index + 1

        if index > 3:
            return head[:index].strip()

        # just cut-off
        return head[:max_length - 3].strip() + u'...'


class UserPreferences(ndb.Model):
    user = ndb.UserProperty()
    userpage_title = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()

    @classmethod
    def save(cls, user, userpage_title):
        keyid = ndb.Key(cls, user.email()).string_id()
        preferences = cls.get_by_id(keyid)
        if preferences is None:
            preferences = cls(id=keyid)
            preferences.user = user
            preferences.created_at = datetime.now()

        preferences.userpage_title = userpage_title
        preferences.put()
        return preferences

    @classmethod
    def get_by_email(cls, email):
        print 1
        keyid = ndb.Key(cls, email).string_id()
        return cls.get_by_id(keyid)

class WikiPage(ndb.Model, PageOperationMixin):
    re_normalize_title = re.compile(ur'([\[\]\(\)\~\!\@\#\$\%\^\&\*\-'
                                    ur'\=\+\\:\;\'\"\,\.\/\?\<\>\s]|'
                                    ur'\bthe\b|\ban?\b)')

    itemtype_path = ndb.StringProperty()
    title = ndb.StringProperty()
    body = ndb.TextProperty()
    description = ndb.StringProperty()
    revision = ndb.IntegerProperty()
    comment = ndb.StringProperty()
    modifier = ndb.UserProperty()
    acl_read = ndb.StringProperty()
    acl_write = ndb.StringProperty()
    inlinks = ndb.JsonProperty()
    outlinks = ndb.JsonProperty()
    related_links = ndb.JsonProperty()
    updated_at = ndb.DateTimeProperty()

    published_at = ndb.DateTimeProperty()
    published_to = ndb.StringProperty()
    older_title = ndb.StringProperty()
    newer_title = ndb.StringProperty()

    @property
    def is_old_revision(self):
        return False

    @property
    def rendered_body(self):
        value = cache.get_rendered_body(self.title)
        if value is None:
            value = super(WikiPage, self).rendered_body
            cache.set_rendered_body(self.title, value)
        return value

    @property
    def metadata(self):
        value = cache.get_metadata(self.title)
        if value is None:
            value = super(WikiPage, self).metadata
            cache.set_metadata(self.title, value)
        return value

    @property
    def hashbangs(self):
        value = cache.get_hashbangs(self.title)
        if value is None:
            value = super(WikiPage, self).hashbangs
            cache.set_hashbangs(self.title, value)
        return value

    def update_content(self, new_body, base_revision, comment, user=None, force_update=False):
        if not force_update and self.body == new_body:
            return False

        # delete rendered body cache
        cache.del_rendered_body(self.title)
        cache.del_hashbangs(self.title)

        # update body
        old_md = self.metadata
        new_md = PageOperationMixin.parse_metadata(new_body)
        cache.del_metadata(self.title)

        # validate contents
        if u'pub' in new_md and u'redirect' in new_md:
            raise ValueError('You cannot use "pub" and "redirect" metadata at '
                             'the same time.')
        if u'redirect' in new_md and len(PageOperationMixin.remove_metadata(new_body).strip()) != 0:
            raise ValueError('Page with "redirect" metadata cannot have a body '
                             'content.')
        if u'read' in new_md and new_md['content-type'] != 'text/x-markdown':
            raise ValueError('You cannot restrict read access of custom content-typed page.')
        if self.revision < base_revision:
            raise ValueError('Invalid revision number: %d' % base_revision)

        # update model fields
        if self.revision != base_revision:
            # perform 3-way merge if needed
            base = WikiPageRevision.query(WikiPageRevision.title == self.title, WikiPageRevision.revision == base_revision).get().body
            merged = ''.join(Merge3(base, self.body, new_body).merge_lines())
            self.body = merged
        else:
            self.body = new_body

        self.modifier = user
        self.description = self.make_description(200)
        self.acl_read = new_md.get('read', '')
        self.acl_write = new_md.get('write', '')
        self.comment = comment
        self.revision += 1

        if not force_update:
            self.updated_at = datetime.now()

        # publish
        pub_old = u'pub' in old_md
        pub_new = u'pub' in new_md
        pub_old_title = None
        pub_new_title = None
        if pub_old:
            pub_old_title = old_md['pub']
        if pub_new:
            pub_new_title = new_md['pub']

        if pub_old and pub_new and (pub_old_title != pub_new_title):
            # if target page is changed
            self._unpublish(save=False)
            self._publish(title=pub_new_title, save=False)
        else:
            if pub_new:
                self._publish(title=pub_new_title, save=False)
            else:
                self._unpublish(save=False)

        # update related pages if it's first time
        if self.revision == 1:
            for _ in range(5):
                self.update_related_links()

        # update itemtype_path
        self.itemtype_path = schema.get_itemtype_path(self.itemtype)

        # save
        self.put()

        # create revision
        rev_key = self._rev_key()
        rev = WikiPageRevision(parent=rev_key, title=self.title, body=self.body,
                               created_at=self.updated_at, revision=self.revision,
                               comment=self.comment, modifier=self.modifier,
                               acl_read=self.acl_read, acl_write=self.acl_write)
        rev.put()

        # update inlinks and outlinks
        old_redir = old_md.get('redirect')
        new_redir = new_md.get('redirect')
        self.update_links(old_redir, new_redir)

        # invalidate cache
        if self.title == '.config':
            cache.del_config()
        if self.revision == 1:
            cache.del_titles()

        return True

    @property
    def revisions(self):
        return WikiPageRevision.query(ancestor=self._rev_key())

    @property
    def link_scoretable(self):
        """Returns all links ordered by score"""

        # related links
        related_links_scoretable = self.related_links

        # in/out links
        inlinks = reduce(lambda a, b: a + b, self.inlinks.values(), [])
        outlinks = reduce(lambda a, b: a + b, self.outlinks.values(), [])
        inout_links = set(inlinks + outlinks).difference(related_links_scoretable.keys())
        inout_links_len = len(inout_links)
        inout_score = 1.0 / inout_links_len if inout_links_len != 0 else 0.0
        inout_links_scoretable = dict(zip(inout_links, [inout_score] * inout_links_len))

        scoretable = dict(inout_links_scoretable.items() + related_links_scoretable.items())
        sorted_scoretable = sorted(scoretable.iteritems(),
                                   key=operator.itemgetter(1),
                                   reverse=True)
        return OrderedDict(sorted_scoretable)

    def update_links(self, old_redir=None, new_redir=None):
        """Updates outlinks of this page and inlinks of target pages"""
        # 1. process "redirect" metadata
        if old_redir != new_redir:
            if old_redir is not None:
                source = WikiPage.get_by_title(old_redir, follow_redirect=True)
            else:
                source = self

            if new_redir is not None:
                target = WikiPage.get_by_title(new_redir, follow_redirect=True)
            else:
                target = self

            for rel, titles in source.inlinks.items():
                for t in titles:
                    page = WikiPage.get_by_title(t)
                    page.del_outlink(source.title, rel)
                    page.add_outlink(target.title, rel)
                    page.put()
                    cache.del_rendered_body(page.title)
                    cache.del_hashbangs(page.title)

                target.add_inlinks(source.inlinks[rel], rel)
                del source.inlinks[rel]

            source.put()
            cache.del_rendered_body(source.title)
            cache.del_hashbangs(source.title)
            target.put()
            cache.del_rendered_body(target.title)
            cache.del_hashbangs(target.title)

        # 2. update in/out links
        cur_outlinks = self.outlinks or {}
        new_outlinks = {}
        for rel, titles in self._parse_outlinks().items():
            new_outlinks[rel] =\
                [WikiPage.get_by_title(t, follow_redirect=True).title
                 for t in titles]
            new_outlinks[rel] = list(set(new_outlinks[rel]))

        if self.acl_read:
            # delete all inlinks of target pages if there's read restriction
            for rel, titles in cur_outlinks.items():
                for title in titles:
                    page = WikiPage.get_by_title(title)
                    try:
                        page.del_inlink(title)
                        if len(page.inlinks) == 0 and page.revision == 0:
                            page.put().delete()
                        else:
                            page.put()
                        cache.del_rendered_body(page.title)
                        cache.del_hashbangs(page.title)
                    except ValueError:
                        pass
        else:
            # update all inlinks of target pages
            added_outlinks = {}
            for rel, titles in new_outlinks.items():
                added_outlinks[rel] = titles
                if rel in cur_outlinks:
                    added_outlinks[rel] =\
                        set(added_outlinks[rel]).difference(cur_outlinks[rel])
            removed_outlinks = {}
            for rel, titles in cur_outlinks.items():
                removed_outlinks[rel] = titles
                if rel in new_outlinks:
                    removed_outlinks[rel] =\
                        set(removed_outlinks[rel]).difference(new_outlinks[rel])

            for rel, titles in added_outlinks.items():
                for title in titles:
                    page = WikiPage.get_by_title(title)
                    page.add_inlink(self.title, rel)
                    page.put()
                    cache.del_rendered_body(page.title)
                    cache.del_hashbangs(page.title)
            for rel, titles in removed_outlinks.items():
                for title in titles:
                    page = WikiPage.get_by_title(title, follow_redirect=True)
                    try:
                        page.del_inlink(self.title, rel)
                        if page.inlinks == {} and page.revision == 0:
                            page.put().delete()
                        else:
                            page.put()
                        cache.del_rendered_body(page.title)
                        cache.del_hashbangs(page.title)
                    except ValueError:
                        pass

        # update outlinks of this page
        self.outlinks = new_outlinks
        for rel in self.outlinks.keys():
            self.outlinks[rel].sort()
        self.put()

    def _publish(self, title, save):
        if self.published_at is not None and self.published_to == title:
            return

        posts = WikiPage.get_published_posts(title, 20)

        if len(posts) > 0:
            latest = posts[0]
            latest.newer_title = self.title
            latest.put()
            self.older_title = latest.title

        self.published_to = title
        self.published_at = datetime.now()

        if save:
            self.put()

        cache.del_rendered_body(self.title)
        cache.del_hashbangs(self.title)
        if self.newer_title:
            cache.del_rendered_body(self.newer_title)
            cache.del_hashbangs(self.newer_title)
        if self.older_title:
            cache.del_rendered_body(self.older_title)
            cache.del_hashbangs(self.older_title)

    def _unpublish(self, save):
        if self.published_at is None:
            return

        cache.del_rendered_body(self.title)
        cache.del_hashbangs(self.title)
        if self.newer_title:
            cache.del_rendered_body(self.newer_title)
            cache.del_hashbangs(self.newer_title)
        if self.older_title:
            cache.del_rendered_body(self.older_title)
            cache.del_hashbangs(self.older_title)

        older = WikiPage.get_by_title(self.older_title)
        newer = WikiPage.get_by_title(self.newer_title)

        if self.older_title is not None and self.newer_title is not None:
            newer.older_title = self.older_title
            older.newer_title = self.newer_title
            newer.put()
            older.put()
        elif self.older_title is not None:
            older.newer_title = None
            older.put()
        elif self.newer_title is not None:
            newer.older_title = None
            newer.put()

        self.published_at = None
        self.published_to = None
        self.older_title = None
        self.newer_title = None

        if save:
            self.put()

    def get_similar_titles(self, user):
        return WikiPage._similar_titles(WikiPage.get_titles(user), self.title)

    def update_related_links(self, max_distance=5):
        """Update related_links score table by random walk"""
        if len(self.outlinks) == 0:
            return

        if self.related_links is None:
            self.related_links = {}

        # random walk
        score_table = self.related_links
        WikiPage._update_related_links(self, self, 0.1, score_table,
                                       max_distance)

        self.related_links = score_table
        self.normalize_related_links()

    def normalize_related_links(self):
        related_links = self.related_links

        # filter out obvious(direct) links
        outlinks = reduce(lambda x, y: x + y, self.outlinks.values(), [])
        inlinks = reduce(lambda x, y: x + y, self.inlinks.values(), [])
        direct_links = set(outlinks + inlinks)
        related_links = dict(filter(lambda (k, v): k not in direct_links, related_links.items()))

        # filter out insignificant links
        if len(related_links) > 30:
            sorted_tuples = sorted(related_links.iteritems(),
                                   key=operator.itemgetter(1))
            related_links = OrderedDict(sorted_tuples[-30:])

        # normalize score
        total = sum(related_links.values())
        if total > 1.0:
            for link, score in related_links.items():
                related_links[link] = score / total

        # done
        self.related_links = related_links

    def _parse_outlinks(self):
        body = WikiPage.remove_metadata(self.body)
        links = md_wikilink.parse_wikilinks(self.itemtype, body)
        unique_links = {}
        for rel, titles in links.items():
            unique_links[rel] = list(set(titles))
        return unique_links

    def add_inlinks(self, titles, rel):
        WikiPage._add_inout_links(self.inlinks, titles, rel)

    def add_outlinks(self, titles, rel):
        WikiPage._add_inout_links(self.outlinks, titles, rel)

    def add_inlink(self, title, rel):
        WikiPage._add_inout_link(self.inlinks, title, rel)

    def add_outlink(self, title, rel):
        WikiPage._add_inout_link(self.outlinks, title, rel)

    def del_inlink(self, title, rel=None):
        WikiPage._del_inout_link(self.inlinks, title, rel)

    def del_outlink(self, title, rel=None):
        WikiPage._del_inout_link(self.outlinks, title, rel)

    @classmethod
    def search(cls, expression):
        # parse
        parsed = search.parse_expression(expression)

        # evaluate
        pos, neg = parsed['pos'], parsed['neg']
        pos_pages = [cls.get_by_title(t, True) for t in pos]
        neg_pages = [cls.get_by_title(t, True) for t in neg]
        scoretable = search.evaluate(
            dict((page.title, page.link_scoretable) for page in pos_pages),
            dict((page.title, page.link_scoretable) for page in neg_pages)
        )

        return scoretable

    @classmethod
    def randomly_update_related_links(cls, iteration, recent=False):
        if recent:
            titles = [p.title for p in WikiPage.get_changes(None)][:iteration]
        else:
            titles = WikiPage.get_titles()

        if len(titles) > iteration:
            titles = random.sample(titles, iteration)
        for title in titles:
            page = cls.get_by_title(title, follow_redirect=True)
            page.update_related_links()
            page.put()
        return titles

    @classmethod
    def _update_related_links(cls, start_page, page, score, score_table,
                              distance):
        if distance == 0:
            return

        #if l != start_page.title
        nested_links = [l for l in page.outlinks.values()]
        links = []
        for l in nested_links:
            links += l
        links = [l for l in links if l != start_page.title]

        if len(links) == 0:
            return

        next_page = WikiPage.get_by_title(random.choice(links), follow_redirect=True)
        next_link = next_page.title
        if next_link not in score_table:
            score_table[next_link] = 0.0

        next_score = score * 0.5
        score_table[next_link] = next_score

        # update target page's relate links
        if next_page.revision > 0:
            if next_page.related_links is None:
                next_page.related_links = {}
            if start_page.title not in next_page.related_links:
                next_page.related_links[start_page.title] = 0.0

            next_page_score = next_score
            next_page.related_links[start_page.title] += next_page_score
            next_page.normalize_related_links()
            next_page.put()

        cls._update_related_links(start_page, next_page, next_score,
                                  score_table, distance - 1)

    @classmethod
    def get_index(cls, user=None):
        q = WikiPage.query(ancestor=WikiPage._key())

        pages = q.order(WikiPage.title).fetch(projection=[
            WikiPage.title,
            WikiPage.acl_write,
            WikiPage.acl_read,
            WikiPage.comment,
            WikiPage.modifier,
            WikiPage.updated_at])

        default_permission = PageOperationMixin.get_default_permission()
        return [page for page in pages
                if page.updated_at and page.can_read(user, default_permission)]

    @classmethod
    def get_titles(cls, user=None):
        email = user.email() if user is not None else u'None'
        titles = cache.get_titles(email)
        if titles is None:
            titles = [page.title for page in cls.get_index(user)]
            cache.set_titles(email, titles)

        return titles

    @staticmethod
    def get_published_posts(title, limit):
        q = WikiPage.query(ancestor=WikiPage._key())
        q = q.filter(WikiPage.published_to == title)
        q = q.filter(WikiPage.published_at != None)
        return list(q.order(-WikiPage.published_at).fetch(limit=limit))

    @classmethod
    def get_changes(cls, user, limit=7, include_body=False):
        q = WikiPage.query(ancestor=WikiPage._key())
        q = q.filter(WikiPage.updated_at != None)

        if limit != 0:
            date_from = datetime.now() - timedelta(days=limit)
            q = q.filter(WikiPage.updated_at >= date_from)

        if include_body:
            pages = q.order(-WikiPage.updated_at).fetch()
        else:
            prjs = [
                WikiPage.title,
                WikiPage.updated_at,
                WikiPage.modifier,
                WikiPage.comment,
                WikiPage.acl_write,
                WikiPage.acl_read,
            ]
            pages = q.order(-WikiPage.updated_at).fetch(projection=prjs)

        default_permission = PageOperationMixin.get_default_permission()
        return [page for page in pages if page.can_read(user, default_permission)]

    @classmethod
    def get_config(cls):
        result = cache.get_config()
        if result is None:
            page = cls.get_by_title('.config')
            result = None
            try:
                result = yaml.load(PageOperationMixin.remove_metadata(page.body))
            except:
                pass

            if result is None:
                result = main.DEFAULT_CONFIG
            else:
                result = dict(main.DEFAULT_CONFIG.items() + result.items())
            cache.set_config(result)
        return result

    @classmethod
    def get_by_title(cls, title, follow_redirect=False):
        key = cls._key()
        page = WikiPage.query(WikiPage.title == title, ancestor=key).get()
        if page is None:
            page = WikiPage(parent=key, title=title, body=u'', revision=0,
                            inlinks={}, outlinks={}, related_links={})
        elif follow_redirect and 'redirect' in page.metadata:
            new_title = page.metadata['redirect']
            page = cls.get_by_title(new_title, follow_redirect)

        return page

    @classmethod
    def title_to_path(cls, title):
        return urllib2.quote(title.replace(u' ', u'_').encode('utf-8'))

    @classmethod
    def path_to_title(cls, path):
        return urllib2.unquote(path).decode('utf-8').replace('_', ' ')

    @classmethod
    def _similar_titles(cls, titles, target):
        normalized_target = cls._normalize_title(target)
        if len(normalized_target) == 0:
            return OrderedDict([
                (u'startswiths', []),
                (u'endswiths', []),
                (u'contains', []),
            ])

        contains = []
        startswiths = []
        endswiths = []
        for title in titles:
            normalized_title = cls._normalize_title(title)
            if normalized_title.find(normalized_target) == -1:
                continue
            if normalized_title.startswith(normalized_target):
                startswiths.append(title)
            elif normalized_title.endswith(normalized_target):
                endswiths.append(title)
            else:
                contains.append(title)

        return OrderedDict([
            (u'startswiths', startswiths),
            (u'endswiths', endswiths),
            (u'contains', contains),
        ])

    @classmethod
    def _normalize_title(cls, title):
        return re.sub(cls.re_normalize_title, u'', title.lower())

    @classmethod
    def _key(cls):
        return ndb.Key(u'wiki', u'/')

    @staticmethod
    def _add_inout_links(links, titles, rel):
        if len(titles) == 0:
            return

        if rel not in links:
            links[rel] = []

        links[rel] += titles
        links[rel].sort()

    @staticmethod
    def _add_inout_link(links, title, rel):
        if rel not in links:
            links[rel] = []
        if title not in links[rel]:
            links[rel].append(title)
            links[rel].sort()

    @staticmethod
    def _del_inout_link(links, title, rel=None):
        if rel is not None and rel in links:
            links[rel].remove(title)
            if len(links[rel]) == 0:
                del links[rel]
        else:
            for rel, titles in links.items():
                titles.remove(title)
                if len(titles) == 0:
                    del links[rel]

    def _rev_key(self):
        return ndb.Key(u'revision', self.title)


class WikiPageRevision(ndb.Model, PageOperationMixin):
    title = ndb.StringProperty()
    body = ndb.TextProperty()
    revision = ndb.IntegerProperty()
    comment = ndb.StringProperty()
    modifier = ndb.UserProperty()
    acl_read = ndb.StringProperty()
    acl_write = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()

    @property
    def is_old_revision(self):
        return True

    @property
    def updated_at(self):
        return self.created_at

    @property
    def inlinks(self):
        return {}

    @property
    def outlinks(self):
        return {}

    @property
    def related_links(self):
        return {}

    @property
    def older_title(self):
        return None

    @property
    def newer_title(self):
        return None


class TocGenerator(object):
    re_headings = ur'<h(\d)>(.+?)</h\d>'

    def __init__(self, html):
        self._html = html
        self._index = 0

    def add_toc(self):
        """Add table of contents to HTML"""
        headings = TocGenerator.extract_headings(self._html)
        outlines = self._generate_outline(headings)
        paths = self._generate_path(outlines)

        if len(headings) > 4:
            toc = u'<div class="toc"><h1>Table of Contents</h1>' \
                  u'%s</div>' % self._generate_toc(outlines, iter(paths))
        else:
            toc = u''

        def replacer(m):
            lev = m.group(1)
            text = m.group(2)
            hashed = TocGenerator.hash_str(paths[self._index])
            html = u'<h%s>%s ' \
                   u'<a id="h_%s" href="#h_%s" class="caret-target">#</a>' \
                   u'</h%s>' % (lev, text, hashed, hashed, lev)

            # insert table of contents before first heading
            if self._index == 0:
                html = toc + html

            self._index += 1
            return html

        return re.sub(TocGenerator.re_headings, replacer, self._html)

    @staticmethod
    def extract_headings(html):
        matches = re.findall(TocGenerator.re_headings, html, flags=re.DOTALL)
        return [(int(m[0]), m[1]) for m in matches]

    @staticmethod
    def hash_str(path):
        m = hashlib.md5()
        m.update(path.encode('utf-8'))
        return m.hexdigest()

    def _generate_outline(self, headings):
        """Generate recursive array of document headings"""
        if len(headings) == 0:
            return []

        cur_lev = headings[0][0]
        if cur_lev != 1:
            raise ValueError('Headings should start from H1')

        _, result = self._outline_children(headings, 0, cur_lev)
        return result

    def _generate_toc(self, outline, path_iter):
        if len(outline) == 0:
            return u''

        parts = [u'<ol>']
        for title, children in outline:
            hashed = TocGenerator.hash_str(path_iter.next())
            parts.append(u'<li>')
            parts.append(u'<div><a href="#h_%s">%s</a></div>' % (hashed, title))
            parts.append(self._generate_toc(children, path_iter))
            parts.append(u'</li>')
        parts.append(u'</ol>')

        return u''.join(parts)

    def _outline_children(self, hs, index, lev):
        result = []
        while len(hs) > index:
            curlev, curtitle = hs[index]
            if curlev == lev:
                index, children = self._outline_children(hs, index + 1, curlev + 1)
                result.append([curtitle, children])
                index += 1
            elif curlev < lev:
                index -= 1
                break
            else:
                raise ValueError('Invalid level of headings')

        return index, result

    def _generate_path(self, outlines):
        result = []
        self._generate_children_path(result, None, outlines)

        duplicates = set([x for x in result if result.count(x) > 1])
        if len(duplicates) > 0:
            raise ValueError("Duplicate paths not allowed: %s" % duplicates.pop())

        return result

    def _generate_children_path(self, result, path, outlines):
        for h, children in outlines:
            if path is not None:
                cur_path = u'%s\t%s' % (path, h)
            else:
                cur_path = h
            result.append(cur_path)
            self._generate_children_path(result, cur_path, children)


regions = {
    u'ㄱ': (u'가', u'나'),
    u'ㄴ': (u'나', u'다'),
    u'ㄷ': (u'다', u'라'),
    u'ㄹ': (u'라', u'마'),
    u'ㅁ': (u'마', u'바'),
    u'ㅂ': (u'바', u'사'),
    u'ㅅ': (u'사', u'아'),
    u'ㅇ': (u'아', u'자'),
    u'ㅈ': (u'자', u'차'),
    u'ㅊ': (u'차', u'카'),
    u'ㅋ': (u'카', u'타'),
    u'ㅌ': (u'타', u'파'),
    u'ㅍ': (u'파', u'하'),
    u'ㅎ': (u'하', u'힣'),
}


def title_grouper(title):
    title = title.upper()
    head = title[0]
    if 'A' <= head <= 'Z' or '0' <= head <= '9':
        return head

    for key, values in regions.items():
        if values[0] <= head < values[1]:
            return key

    return 'Misc'


md = markdown.Markdown(
    extensions=[
        md_wikilink.WikiLinkExtension(),
        md_itemprop.ItemPropExtension(),
        md_url.URLExtension(),
        md_mathjax.MathJaxExtension(),
        DefListExtension(),
    ],
    safe_mode=False,
)
