# -*- coding: utf-8 -*-
import re
import yaml
import main
import random
import schema
import search
import caching
import logging
import urllib2
import operator
from bzrlib.merge3 import Merge3
from collections import OrderedDict
from google.appengine.ext import ndb
from datetime import datetime, timedelta
from google.appengine.ext import deferred
from markdownext import md_wikilink, md_checkbox

from models import PageOperationMixin, ConflictError, WikiPageRevision, TocGenerator, SchemaDataIndex
from models import is_admin_user, md


logging.getLogger().setLevel(logging.DEBUG)


class WikiPage(ndb.Model, PageOperationMixin):
    re_normalize_title = re.compile(ur'([\[\]\(\)\~\!\@\#\$\%\^\&\*\-'
                                    ur'\=\+\\:\;\'\"\,\.\?\<\>\s]|'
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
        value = caching.get_rendered_body(self.title)
        if value is None:
            value = super(WikiPage, self).rendered_body
            caching.set_rendered_body(self.title, value)
        return value

    @property
    def data(self):
        value = caching.get_data(self.title)
        if value is None:
            value = super(WikiPage, self).data
            caching.set_data(self.title, value)
        return value

    @property
    def metadata(self):
        value = caching.get_metadata(self.title)
        if value is None:
            value = super(WikiPage, self).metadata
            caching.set_metadata(self.title, value)
        return value

    @property
    def hashbangs(self):
        value = caching.get_hashbangs(self.title)
        if value is None:
            value = super(WikiPage, self).hashbangs
            caching.set_hashbangs(self.title, value)
        return value

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

    def preview_rendered_body(self, body):
        """Preview rendered body without updating model"""
        self.body = body
        return super(WikiPage, self).rendered_body

    def can_write(self, user, default_acl=None):
        if default_acl is None:
            default_acl = WikiPage.get_default_permission()
        return super(WikiPage, self).can_write(user, default_acl)

    def can_read(self, user, default_acl=None):
        if default_acl is None:
            default_acl = WikiPage.get_default_permission()
        return super(WikiPage, self).can_read(user, default_acl)

    def delete(self, user=None):
        if not is_admin_user(user):
            raise RuntimeError('Only admin can delete pages.')

        self.update_content('', self.revision, user=user, dont_create_rev=True, dont_defer=True)
        self.related_links = {}
        self.modifier = None
        self.updated_at = None
        self.revision = 0
        self.put()

        keys = [r.key for r in self.revisions]
        ndb.delete_multi(keys)

        caching.del_titles()

    def update_content(self, content, base_revision, comment='', user=None, force_update=False, dont_create_rev=False, dont_defer=False, partial='all'):
        if partial == 'all':
            return self._update_content_all(content, base_revision, comment, user, force_update, dont_create_rev, dont_defer)
        elif partial.startswith('checkbox'):
            return self._update_content_checkbox(content, base_revision, comment, user, force_update, dont_create_rev, dont_defer, partial)
        else:
            raise ValueError('Invalid partial expression: %s' % partial)

    def _update_content_checkbox(self, content, base_revision, comment, user, force_update, dont_create_rev, dont_defer, exp):
        cur_body = PageOperationMixin.remove_metadata(self.body).strip()
        cur_index = {'value': -1}
        index = int(re.match(ur'checkbox\[(\d+)]', exp).group(1))

        def replacer(m):
            cur_index['value'] += 1
            if cur_index['value'] != index:
                return m.group(0)
            else:
                return u'[x]' if content == u'1' else u'[ ]'

        new_body = re.sub(md_checkbox.RE_CHECKBOX, replacer, cur_body)

        return self._update_content_all(new_body, base_revision, comment, user, force_update, dont_create_rev, dont_defer)

    def _update_content_all(self, new_body, base_revision, comment, user, force_update, dont_create_rev, dont_defer):
        if not force_update and self.body == new_body:
            return False

        # get old data amd metadata
        old_md = self.metadata
        old_data = self.data

        # validate contents
        ## validate schema data
        new_md = PageOperationMixin.parse_metadata(new_body)
        try:
            PageOperationMixin.parse_data(self.title, new_md['schema'], new_body)
        except Exception:
            raise ValueError('Invalid schema data')

        ## validate metadata
        if u'pub' in new_md and u'redirect' in new_md:
            raise ValueError('You cannot use "pub" and "redirect" metadata at '
                             'the same time.')
        if u'redirect' in new_md and len(PageOperationMixin.remove_metadata(new_body).strip()) != 0:
            raise ValueError('Page with "redirect" metadata cannot have a body '
                             'content.')
        if u'read' in new_md and new_md['content-type'] != 'text/x-markdown':
            raise ValueError('You cannot restrict read access of custom content-typed page.')

        ## validate revision
        if self.revision < base_revision:
            raise ValueError('Invalid revision number: %d' % base_revision)

        ## validate ToC
        if not TocGenerator(md.convert(new_body)).validate():
            raise ValueError("Duplicate paths not allowed")

        if self.revision != base_revision:
            # perform 3-way merge if needed
            base = WikiPageRevision.query(WikiPageRevision.title == self.title, WikiPageRevision.revision == base_revision).get().body
            merged = ''.join(Merge3(base, self.body, new_body).merge_lines())
            conflicted = len(re.findall(PageOperationMixin.re_conflicted, merged)) > 0
            if conflicted:
                raise ConflictError('Conflicted', base, new_body, merged)
            else:
                new_body = merged

        # delete rendered body, metadata, data cache
        caching.del_rendered_body(self.title)
        caching.del_hashbangs(self.title)
        caching.del_metadata(self.title)
        caching.del_data(self.title)

        # update model fields
        self.body = new_body
        self.modifier = user
        self.description = self.make_description()
        self.acl_read = new_md.get('read', '')
        self.acl_write = new_md.get('write', '')
        self.comment = comment
        if not dont_create_rev:
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

        # update itemtype_path
        self.itemtype_path = schema.get_itemtype_path(new_md['schema'])

        # save
        self.put()

        # create revision
        if not dont_create_rev:
            rev_key = self._rev_key()
            rev = WikiPageRevision(parent=rev_key, title=self.title, body=self.body,
                                   created_at=self.updated_at, revision=self.revision,
                                   comment=self.comment, modifier=self.modifier,
                                   acl_read=self.acl_read, acl_write=self.acl_write)
            rev.put()

        # deferred update schema data index
        new_data = self.data
        if dont_defer:
            self.update_data_index(old_data, new_data)
        else:
            deferred.defer(self.update_data_index, old_data, new_data)

        # update inlinks and outlinks
        old_redir = old_md.get('redirect')
        new_redir = new_md.get('redirect')
        if dont_defer:
            self.update_links(old_redir, new_redir)
        else:
            deferred.defer(self.update_links, old_redir, new_redir)

        # delete config and title cache
        if self.title == '.config':
            caching.del_config()
        if self.revision == 1:
            caching.del_titles()

        return True

    def rebuild_data_index(self):
        # delete all index for this page
        keys = [i.key for i in SchemaDataIndex.query(SchemaDataIndex.title == self.title).fetch()]
        ndb.delete_multi(keys)

        # insert
        data = self.data
        entities = [SchemaDataIndex(title=self.title, name=name, value=value) for name, value in WikiPage._data_as_pairs(data)]
        ndb.put_multi(entities)

    def update_data_index(self, old_data, new_data):
        old_pairs = WikiPage._data_as_pairs(old_data)
        new_pairs = WikiPage._data_as_pairs(new_data)

        deletes = old_pairs.difference(new_pairs)
        inserts = new_pairs.difference(old_pairs)

        # delete
        queries = [SchemaDataIndex.query(SchemaDataIndex.title == self.title, SchemaDataIndex.name == name, SchemaDataIndex.value == value)
                   for name, value in deletes]
        entities = reduce(lambda a, b: a + b, [q.fetch() for q in queries], [])
        keys = [e.key for e in entities]
        ndb.delete_multi(keys)

        # insert
        entities = [SchemaDataIndex(title=self.title, name=name, value=value) for name, value in inserts]
        ndb.put_multi(entities)

    def update_links(self, old_redir, new_redir):
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
                    caching.del_rendered_body(page.title)
                    caching.del_hashbangs(page.title)

                target.add_inlinks(source.inlinks[rel], rel)
                del source.inlinks[rel]

            source.put()
            caching.del_rendered_body(source.title)
            caching.del_hashbangs(source.title)
            target.put()
            caching.del_rendered_body(target.title)
            caching.del_hashbangs(target.title)

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
                        caching.del_rendered_body(page.title)
                        caching.del_hashbangs(page.title)
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
                    caching.del_rendered_body(page.title)
                    caching.del_hashbangs(page.title)
            for rel, titles in removed_outlinks.items():
                for title in titles:
                    page = WikiPage.get_by_title(title, follow_redirect=True)
                    try:
                        page.del_inlink(self.title, rel)
                        if page.inlinks == {} and page.revision == 0:
                            page.put().delete()
                        else:
                            page.put()
                        caching.del_rendered_body(page.title)
                        caching.del_hashbangs(page.title)
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

        posts = WikiPage.get_posts_of(title, 1)

        if len(posts) > 0:
            latest = posts[0]
            latest.newer_title = self.title
            latest.put()
            self.older_title = latest.title

        self.published_to = title
        self.published_at = datetime.now()

        if save:
            self.put()

        caching.del_rendered_body(self.title)
        caching.del_hashbangs(self.title)
        if self.newer_title:
            caching.del_rendered_body(self.newer_title)
            caching.del_hashbangs(self.newer_title)
        if self.older_title:
            caching.del_rendered_body(self.older_title)
            caching.del_hashbangs(self.older_title)

    def _unpublish(self, save):
        if self.published_at is None:
            return

        caching.del_rendered_body(self.title)
        caching.del_hashbangs(self.title)
        if self.newer_title:
            caching.del_rendered_body(self.newer_title)
            caching.del_hashbangs(self.newer_title)
        if self.older_title:
            caching.del_rendered_body(self.older_title)
            caching.del_hashbangs(self.older_title)

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
        return WikiPage.similar_titles(WikiPage.get_titles(user), self.title)

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

    def get_posts(self, limit):
        return WikiPage.get_posts_of(self.title, limit)

    def _schema_item_to_links(self, name, values):
        itemtype = self.itemtype

        if type(values) == list:
            links = {}
            for value in values:
                for key, parsed_values in md_wikilink.parse_wikilinks(itemtype, u'[[%s::%s]]' % (name, value)).items():
                    if key not in links:
                        links[key] = []
                    links[key] += parsed_values
        else:
            links = md_wikilink.parse_wikilinks(self.itemtype, u'[[%s::%s]]' % (name, values))

        return links

    def _parse_outlinks(self):
        unique_links = {}
        itemtype = self.itemtype

        # Add links in hierarchical title
        anscestors = {path[0] for path in self.paths[:-1]}
        if len(anscestors) > 0:
            unique_links['%s/relatedTo' % itemtype] = anscestors

        # Add links in body
        links = md_wikilink.parse_wikilinks(itemtype, WikiPage.remove_metadata(self.body))
        for rel, titles in links.items():
            if rel not in unique_links:
                unique_links[rel] = set()
            unique_links[rel].update(titles)

        # Add links in structured data
        for name, value in self.data.items():
            if not self._is_schema_item_link(name):
                continue

            links = self._schema_item_to_links(name, value)

            for rel, titles in links.items():
                if rel not in unique_links:
                    unique_links[rel] = set()
                unique_links[rel].update(titles)

        # turn sets into lists
        for key in unique_links.keys():
            unique_links[key] = list(unique_links[key])

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

    def _rev_key(self):
        return ndb.Key(u'revision', self.title)

    @classmethod
    def get_config(cls):
        result = caching.get_config()
        if result is None:
            result = main.DEFAULT_CONFIG

            try:
                config_page = cls.get_by_title('.config')
                user_config = yaml.load(PageOperationMixin.remove_metadata(config_page.body))
            except:
                user_config = None
            user_config = user_config or {}

            def merge_dict(target_dict, source_dict):
                for (key, value) in source_dict.iteritems():
                    if type(value) != dict:
                        target_dict[key] = value
                    else:
                        merge_dict(target_dict.setdefault(key, {}), value)

            merge_dict(result, user_config)

            caching.set_config(result)
        return result

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

        default_permission = WikiPage.get_default_permission()
        return [page for page in pages
                if page.updated_at and page.can_read(user, default_permission)]

    @classmethod
    def get_titles(cls, user=None):
        email = user.email() if user is not None else u'None'
        titles = caching.get_titles(email)
        if titles is None:
            titles = {page.title for page in cls.get_index(user)}
            caching.set_titles(email, titles)

        return titles

    @classmethod
    def get_posts_of(cls, title, limit):
        q = cls.query(ancestor=cls._key())
        q = q.filter(cls.published_to == title)
        q = q.filter(cls.published_at != None)
        return list(q.order(-cls.published_at).fetch(limit=limit))

    @classmethod
    def get_changes(cls, user, limit=7):
        q = WikiPage.query(ancestor=WikiPage._key())
        q = q.filter(WikiPage.updated_at != None)

        if limit != 0:
            date_from = datetime.now() - timedelta(days=limit)
            q = q.filter(WikiPage.updated_at >= date_from)

        prjs = [
            WikiPage.title,
            WikiPage.updated_at,
            WikiPage.modifier,
            WikiPage.comment,
            WikiPage.acl_write,
            WikiPage.acl_read,
        ]
        pages = q.order(-WikiPage.updated_at).fetch(projection=prjs)

        default_permission = WikiPage.get_default_permission()
        return [page for page in pages if page.can_read(user, default_permission)]

    @classmethod
    def wikiquery(cls, q, user=None):
        email = user.email() if user is not None else 'None'
        results = caching.get_wikiquery(q, email)
        if results is None:
            page_query, attrs = search.parse_wikiquery(q)
            titles = cls._evaluate_pages(page_query)
            accessible_titles = WikiPage.get_titles(user).intersection(titles)

            results = []
            if attrs == [u'name']:
                for title in accessible_titles:
                    results.append({u'name': title})
            else:
                for title in accessible_titles:
                    pagedata = WikiPage.get_by_title(title, follow_redirect=True).data
                    results.append(OrderedDict((attr, pagedata[attr] if attr in pagedata else None) for attr in attrs))

            if len(results) == 1:
                results = results[0]

            caching.set_wikiquery(q, email, results)
        return results

    @classmethod
    def _evaluate_pages(cls, q):
        if len(q) == 1:
            pages = cls._evaluate_pages(q[0])
        elif len(q) == 2:
            pages = cls._evaluate_page_query_term(q[0], q[1])
        else:
            pages = cls._evaluate_page_query_expr(q[0], q[1], q[2:])
        return pages

    @classmethod
    def _evaluate_page_query_term(cls, name, value):
        if name == 'schema' and value.find('/') == -1:
            value = schema.get_itemtype_path(value)
        return [index.title for index in SchemaDataIndex.query(SchemaDataIndex.name == name, SchemaDataIndex.value == value)]

    @classmethod
    def _evaluate_page_query_expr(cls, operand, op, rest):
        pages1 = cls._evaluate_pages(operand)
        pages2 = cls._evaluate_pages(rest)

        if op == '*':
            return set(pages1).intersection(pages2)
        elif op == '+':
            return set(pages1).union(pages2)
        else:
            raise ValueError('Invalid operator: %s' % op)

    @classmethod
    def get_by_path(cls, path, follow_redirect=False):
        return cls.get_by_title(cls.path_to_title(path), follow_redirect)

    @classmethod
    def get_by_title(cls, title, follow_redirect=False):
        if title is None:
            return None
        if title[0] == u'=':
            raise ValueError(u'WikiPage title cannot starts with "="')

        key = cls._key()
        page = WikiPage.query(WikiPage.title == title, ancestor=key).get()
        if page is None:
            page = WikiPage(parent=key, title=title, body=u'', revision=0,
                            inlinks={}, outlinks={}, related_links={})
        elif follow_redirect:
            page = cls._follow_redirect(page)

        return page

    @classmethod
    def _follow_redirect(cls, page):
        trail = {page.title}
        while 'redirect' in page.metadata:
            next_title = page.metadata['redirect']
            if next_title in trail:
                raise ValueError('Circular redirection detected')
            page = cls.get_by_title(next_title)
        return page

    @classmethod
    def title_to_path(cls, title):
        return PageOperationMixin.escape_title(title)

    @classmethod
    def path_to_title(cls, path):
        return urllib2.unquote(path).decode('utf-8').replace('_', ' ')

    @classmethod
    def similar_titles(cls, titles, target):
        normalized_target = cls.normalize_title(target)
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
            if title == target:
                continue

            normalized_title = cls.normalize_title(title)

            if normalized_title.find(normalized_target) == -1:
                pass
            elif normalized_title.startswith(normalized_target):
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
    def normalize_title(cls, title):
        return re.sub(cls.re_normalize_title, u'', title.lower())

    @classmethod
    def _key(cls):
        return ndb.Key(u'wiki', u'/')

    @classmethod
    def rebuild_all_data_index(cls, page_index=0):
        logging.debug('Rebuilding data index: %d' % page_index)

        batch_size = 20
        all_pages = list(cls.query().fetch(batch_size, offset=page_index * batch_size))
        if len(all_pages) == 0:
            logging.debug('Rebuilding data index: Finished!')
            return

        for p in all_pages:
            p.rebuild_data_index()

        deferred.defer(cls.rebuild_all_data_index, page_index + 1)

    @classmethod
    def get_default_permission(cls):
        try:
            return cls.get_config()['service']['default_permissions']
        except KeyError:
            return main.DEFAULT_CONFIG['service']['default_permissions']

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

    @staticmethod
    def _data_as_pairs(data):
        pairs = set()
        for key, value in data.items():
            if type(value) == list:
                for v in value:
                    pairs.add((key, v))
            else:
                pairs.add((key, value))
        return pairs
