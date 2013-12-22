# -*- coding: utf-8 -*-

import re
import yaml
import main
import cache
import schema
import logging
import operator
import urllib2
from collections import OrderedDict
from markdownext import md_wikilink 
from lxml.html.clean import Cleaner

from models import md, is_admin_user
from models import TocGenerator

logging.getLogger().setLevel(logging.DEBUG)

class PageOperationMixin(object):
    re_img = re.compile(ur'<p><img( .+? )/></p>')
    re_metadata = re.compile(ur'^\.([^\s]+)(\s+(.+))?$')
    re_data = re.compile(ur'({{|\[\[)(?P<name>[^\]}]+)::(?P<value>[^\]}]+)(}}|\]\])')
    re_yaml_schema = re.compile(ur'(?:\s{4}|\t)#!yaml/schema[\n\r]+(((?:\s{4}|\t).+[\n\r]+?)+)')
    re_conflicted = re.compile(ur'<<<<<<<.+=======.+>>>>>>>', re.DOTALL)
    re_special_titles_years = re.compile(ur'^(10000|\d{1,4})( BCE)?$')
    re_special_titles_dates = re.compile(ur'^((?P<month>January|February|March|'
                                         ur'April|May|June|July|August|'
                                         ur'September|October|November|'
                                         ur'December)( (?P<date>[0123]?\d))?)$')

    @property
    def rendered_data(self):
        data = [(n, v, schema.humane_property(self.itemtype, n))
                for n, v in self.data.items()
                if n not in ['schema', 'inlinks', 'outlinks']]

        if len(data) == 1:
            # only name and schema?
            return ''

        html = [
            u'<div class="structured-data">',
            u'<h1>Structured data</h1>',
            u'<dl>',
        ]

        data = sorted(data, key=operator.itemgetter(2))

        for name, value, humane_name in data:
            html.append(u'<dt class="key key-%s">%s</dt>' % (name, humane_name))
            if type(value) == list:
                for v in value:
                    html.append(u'<dd class="value value-%s">%s</dd>' % (name, self._render_data_item(name, v)))
            else:
                html.append(u'<dd class="value value-%s">%s</dd>' % (name, self._render_data_item(name, value)))
        html.append(u'</dl></div>')
        return '\n'.join(html)

    def _render_data_item(self, name, value):
        if self._is_schema_item_link(name):
            return u'<span itemprop="%s">%s</span>' % (name, md_wikilink.render_wikilink(value))
        else:
            return u'<span itemprop="%s">%s</span>' % (name, value)

    @property
    def rendered_body(self):
        # body
        body_parts = [PageOperationMixin.remove_metadata(self.body)]

        # incoming links
        if len(self.inlinks) > 0:
            lines = [u'# Incoming Links']
            for rel, links in self.inlinks.items():
                itemtype, rel = rel.split('/')
                lines.append(u'## %s' % schema.humane_property(itemtype, rel, True))

                # remove dups and sort
                links = list(set(links))
                links.sort()

                lines += [u'* [[%s]]' % title for title in links]
            body_parts.append(u'\n'.join(lines))

        # related links
        related_links = self.related_links_by_score
        if len(related_links) > 0:
            lines = [u'# Suggested Pages']
            lines += [u'* {{.score::%.3f}} [[%s]]\n{.noli}' % (score, title)
                      for title, score in related_links.items()[:10]]
            body_parts.append(u'\n'.join(lines))

        # other posts
        if self.older_title or self.newer_title:
            lines = [u'# Other Posts']
            if self.newer_title:
                lines.append(u'* {{.newer::newer}} [[%s]]\n{.noli}' % self.newer_title)
            if self.older_title:
                lines.append(u'* {{.older::older}} [[%s]]\n{.noli}' % self.older_title)
            body_parts.append(u'\n'.join(lines))

        # remove yaml/schema block
        joined = u'\n'.join(body_parts)
        joined = re.sub(PageOperationMixin.re_yaml_schema, u'\n', joined)

        # render to html
        rendered = md.convert(joined)

        # add table of contents
        rendered = TocGenerator(rendered).add_toc()

        # add class for embedded image
        rendered = PageOperationMixin.re_img.sub(u'<p class="img-container"><img \\1/></p>', rendered)

        # add structured data block
        rendered = self.rendered_data + rendered

        # sanitize
        if rendered:
            cleaner = Cleaner(safe_attrs_only=False)
            cleaner.host_whitelist = (
                'www.youtube.com',
                'player.vimeo.com',
            )
            rendered = cleaner.clean_html(rendered)

            # remove div wrapper if there is one
            if rendered.startswith('<div>'):
                rendered = rendered[5:-6]

        return rendered


    @staticmethod
    def escape_title(path):
        return urllib2.quote(path.replace(u' ', u'_').encode('utf-8'))

    @property
    def absolute_url(self):
        return u'/%s' % PageOperationMixin.escape_title(self.title)

    @property
    def revision_list_url(self):
        return u'/%s?rev=list' % PageOperationMixin.escape_title(self.title)

    @property
    def absolute_newer_url(self):
        return u'/%s' % PageOperationMixin.escape_title(self.newer_title)

    @property
    def absolute_older_url(self):
        return u'/%s' % PageOperationMixin.escape_title(self.older_title)

    @property
    def data(self):
        data = PageOperationMixin.parse_data(self.title, self.itemtype, self.body)

        for rel, links in self.inlinks.items():
            if not rel.endswith('/relatedTo'):
                continue
            if 'inlinks' not in data:
                data['inlinks'] = []
            data['inlinks'] += links

        for rel, links in self.outlinks.items():
            if not rel.endswith('/relatedTo'):
                continue
            if 'outlinks' not in data:
                data['outlinks'] = []
            data['outlinks'] += links

        return data

    @property
    def metadata(self):
        return PageOperationMixin.parse_metadata(self.body)

    def can_read(self, user, default_acl=None):
        if default_acl is None:
            default_acl = PageOperationMixin.get_default_permission()

        acl = self.acl_read.split(',') if self.acl_read else []
        acl = acl or default_acl['read']

        if u'all' in acl or len(acl) == 0:
            return True
        elif u'login' in acl and user is not None:
            return True
        elif user is not None and (user.email() in acl or user.email() in self.acl_write.split(',')):
            return True
        elif is_admin_user(user):
            return True
        else:
            return False

    def can_write(self, user, default_acl=None):
        if default_acl is None:
            default_acl = PageOperationMixin.get_default_permission()

        acl = self.acl_write.split(',') if self.acl_write is not None and len(self.acl_write) != 0 else []
        if len(acl) == 0:
            acl = default_acl['write']

        if (not self.can_read(user, default_acl)) and (user is None or user.email() not in acl):
            return False
        elif 'all' in acl:
            return True
        elif (len(acl) == 0 or u'login' in acl) and user is not None:
            return True
        elif user is not None and user.email() in acl:
            return True
        elif is_admin_user(user):
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
        m = re.match(PageOperationMixin.re_special_titles_dates, self.title)
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

    def _is_schema_item_link(self, name):
        if name in ['name', 'schema', 'inlinks', 'outlinks']:
            return False
        elif self.itemtype == 'Book' and name in ['isbn']:
            return False
        else:
            return True

    @classmethod
    def get_config(cls):
        result = cache.get_config()
        if result is None:
            result = main.DEFAULT_CONFIG

            try:
                from models import WikiPage
                page = WikiPage.get_config_page()
                user_config = yaml.load(PageOperationMixin.remove_metadata(page.body))
            except:
                user_config = None
            user_config = user_config or {}

            def merge_dict(target_dict, source_dict):
                for (key,value) in source_dict.iteritems():
                    if type(value) != dict:
                        target_dict[key] = value
                    else:
                        merge_dict(target_dict.setdefault(key, {}), value)

            merge_dict(result, user_config)

            cache.set_config(result)
        return result

    
    @staticmethod
    def get_default_permission():
        try:
            return PageOperationMixin.get_config()['service']['default_permissions']
        except KeyError:
            return main.DEFAULT_CONFIG['service']['default_permissions']

    @staticmethod
    def parse_data(title, itemtype, body):
        matches = {
            'name': title,
            'schema': schema.get_itemtype_path(itemtype)
        }

        # parse data in yaml/schema section
        m = re.search(PageOperationMixin.re_yaml_schema, body)
        if m:
            parsed_yaml = yaml.load(m.group(1))
            if type(parsed_yaml) != dict:
                raise ValueError('YAML must be a dictionary')

            for name, value in parsed_yaml.items():
                if name in matches:
                    if type(matches[name]) != list:
                        matches[name] = [matches[name]]
                    if type(value) == list:
                        matches[name] += value
                    else:
                        matches[name].append(value)
                else:
                    matches[name] = value

        # parse data embedded in body text
        for m in re.finditer(PageOperationMixin.re_data, body):
            name = m.group('name')
            value = m.group('value')
            if name in matches:
                if type(matches[name]) != list:
                    matches[name] = [matches[name]]
                matches[name].append(value)
            else:
                matches[name] = value

        # remove duplicated values
        dedup = {}
        for key, value in matches.items():
            if type(value) is list:
                dedup[key] = list(set(value))
            else:
                dedup[key] = value

        return dedup

    @staticmethod
    def parse_metadata(body):
        matches = []
        for line in body.split(u'\n'):
            m = re.match(PageOperationMixin.re_metadata, line.strip())
            if m:
                matches.append(m)
            else:
                break

        metadata = {
            'content-type': 'text/x-markdown',
            'schema': 'Article',
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
            m = re.match(PageOperationMixin.re_metadata, line.strip())
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
        # remove yaml/schema block and metadata
        body = re.sub(PageOperationMixin.re_yaml_schema, u'\n', self.body)
        body = PageOperationMixin.remove_metadata(body).strip()

        # try newline
        index = body.find(u'\n')
        if index != -1:
            body = body[:index].strip()

        # try period
        index = 0
        while index < max_length:
            next_index = body.find(u'. ', index)
            if next_index == -1:
                break
            index = next_index + 1

        if index > 3:
            return body[:index].strip()

        if len(body) <= max_length:
            return body

        # just cut-off
        return body[:max_length - 3].strip() + u'...'


