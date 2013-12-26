#!/usr/bin/python2.5
#
# App Engine datastore cache functionality.
#
# Copyright 2009 DeWitt Clinton
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import google.appengine.ext.db as db
import logging
import pickle
import sys
import time

class CacheEntry(db.Model):
  """Cache entries contain pickled values and expiration times.
  
  Entries use CacheNamespace as their ancestor entity groups.
  """
  value = db.BlobProperty()
  expires_at = db.IntegerProperty()


class CacheNamespace(db.Model):
  """Cache namespaces are stored as ancestor entity groups."""


class CacheStatistics(db.Model):
  """Cache statitistics are persisted in a single entity."""
  hits = db.IntegerProperty(default=0)
  misses = db.IntegerProperty(default=0)
  items = db.IntegerProperty(default=0)


class Client(object):

  _data = dict()
  _entity_groups = dict()

  _MAX_EXPIRES_IN = 60 * 60 * 24 * 31  # one month in seconds
  _NO_EXPIRATION = sys.maxint  # TODO(dewitt): Replace with max long
  _DEFAULT_NAMESPACE = '_default_'
  _MAX_ENTRIES_PER_NAMESPACE = 1000
  _MAX_NAMESPACES = 100

  _DELETE_NETWORK_FAILURE = 0
  _DELETE_ITEM_MISSING = 1
  _DELETE_SUCCESSFUL = 2

  def __init__(self, default_time=_NO_EXPIRATION, gettime=time.time):
    self._gettime = gettime
    self._default_time = default_time

  def _get_entity_group(self, namespace):
    # Set up the namespace if necessary
    if not namespace:
      namespace = self._DEFAULT_NAMESPACE
    try:
      return self._entity_groups[namespace]
    except KeyError:
      entity_group = CacheNamespace(key_name=namespace)
      entity_group.put()
      self._entity_groups[namespace] = entity_group
      return entity_group

  def _get_entry_key(self, entity_group, key):
    # Return a db.Key for the given key under the entity_group namespace
    return db.Key.from_path(
      entity_group.kind(), entity_group.key().name(), 'CacheEntry', 'key:' + key)

  def _get_statistics_key(self, entity_group):
    # Return a db.Key for the statistics under the given entity_group namespace
    return db.Key.from_path(
      entity_group.kind(), entity_group.key().name(), 'CacheStatistics', 'key')

  def set(self, key, value, time=None, min_compress_len=0, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(self._set, entity_group, key, value, time=time)

  def _set(self, entity_group, key, value, time=None):
    if not time:
      time = self._default_time
    # Compute the expiration time
    if time <= self._MAX_EXPIRES_IN:  # time is a delta in seconds
      expires_at = self._gettime() + time
    else:  # time is seconds since the epoch
      expires_at = time
    return self._set_entry(entity_group, key, value, expires_at)

  def _set_entry(self, entity_group, key, value, expires_at):
    # Ignore the (hash_value, string) form of keys
    if isinstance(key, tuple):
      key = key[1]
    entry_key = self._get_entry_key(entity_group, key)
    old_entry = db.get(entry_key)
    if not old_entry:  # didn't already exist
      self._incr_items(entity_group)
    entry = CacheEntry(key=entry_key)
    entry.expires_at = long(expires_at)
    entry.value = pickle.dumps(value)
    entity = entry.put()
    if entity:
      return True
    else:
      return False

  def set_multi(self,
                mapping,
                time=None,
                key_prefix='',
                min_compress_len=0,
                namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._set_multi, entity_group, mapping, time=time, key_prefix=key_prefix)

  def _set_multi(self, entity_group, mapping, time=None, key_prefix=''):
    not_set = list()
    for key, value in mapping.iteritems():
      if not self._set(entity_group, key_prefix + key, value, time=time):
        not_set.append(key)
    return not_set

  def get(self, key, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(self._get, entity_group, key)

  def _get(self, entity_group, key):
    try:
      entry = self._get_entry(entity_group, key)
    except KeyError:
      self._incr_misses(entity_group)
      return None
    if self._gettime() > entry.expires_at:
      self._incr_misses(entity_group)
      self._delete(entity_group, key)
      return None
    else:
      self._incr_hits(entity_group)
      return pickle.loads(entry.value)

  def _get_entry(self, entity_group, key):
    """Returns entry, raises KeyError if not found."""
    # Ignore the (hash_value, string) form of keys
    if isinstance(key, tuple):
      key = key[1]
    # Retrieve the entry and return it, expired or not, raising KeyError
    entry_key = self._get_entry_key(entity_group, key)
    entry = CacheEntry.get(entry_key)
    if not entry:
      raise KeyError
    return entry

  def get_multi(self, keys, key_prefix='', namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._get_multi, entity_group, keys, key_prefix=key_prefix)

  def _get_multi(self, entity_group, keys, key_prefix=''):
    results = dict()
    for key in keys:
      results[key] = self._get(entity_group, key_prefix + key)
    return results

  def delete(self, key, seconds=0, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._delete, entity_group, key, seconds=seconds)

  def _delete(self, entity_group, key, seconds=0):
    # If we're supposed to block adds for a number of seconds
    if seconds:
      expires_at = self._gettime() + seconds
      self._set(entity_group, key, None, time=expires_at)
    else:
      entry = self._get_entry(entity_group, key)
      if entry:
        self._decr_items(entity_group)
        entry.delete()
      else:
        return self._DELETE_ITEM_MISSING
    return self._DELETE_SUCCESSFUL

  def delete_multi(self, keys, seconds=0, key_prefix='', namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._delete_multi, entity_group, keys, key_prefix=key_prefix, seconds=seconds)

  def _delete_multi(self, entity_group, keys, seconds=0, key_prefix=''):
    statuses = list()
    for key in keys:
      statuses.append(
        self._delete(entity_group, key_prefix + key, seconds=seconds))
    return all(statuses)

  def add(self, key, value, time=0, min_compress_len=0, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(self._add, entity_group, key, value, time=time)

  def _add(self, entity_group, key, value, time=0):
    try:
      entry = self._get_entry(entity_group, key)
      if self._gettime() <= entry.expires_at:
        return False  # The extry exist and hasn't expired
      # The entry existed, but has expired, so we can set it again below
    except KeyError:
      pass  # the key doesn't exist, so we can set it
    self._set(entity_group, key, value, time=time)
    return True

  def add_multi(self,
                mapping,
                time=0,
                key_prefix='',
                min_compress_len=0,
                namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._add_multi, entity_group, mapping, time=time, key_prefix=key_prefix)

  def _add_multi(self, entity_group, mapping, time=0, key_prefix=''):
    not_set = list()
    for key, value in mapping.iteritems():
      if not self._add(entity_group, key_prefix + key, value, time=time):
        not_set.append(key)
    return not_set

  def replace(self, key, value, time=0, min_compress_len=0, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._replace, entity_group, key, value, time=time)

  def _replace(self, entity_group, key, value, time=0):
    try:
      entry = self._get_entry(entity_group, key)
      if self._gettime() <= entry.expires_at:  # Unexpired entries
        self._set(entity_group, key, value, time=time)
        return True
      else:
        self._delete(entity_group, key)  # Delete expired entries
        return False
    except KeyError:
      return False  # the entry doesn't exist, so we can't replace it

  def replace_multi(self,
                    mapping,
                    time=0,
                    key_prefix='',
                    min_compress_len=0,
                    namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(
      self._replace_multi, entity_group, mapping, time=time, key_prefix=key_prefix)

  def _replace_multi(self,
                     entity_group,
                     mapping,
                     time=0,
                     key_prefix=''):
    not_set = list()
    for key, value in mapping.iteritems():
      if not self._replace(entity_group, key_prefix + key, value, time=time):
        not_set.append(key)
    return not_set

  def incr(self, key, delta=1, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(self._incr, entity_group, key, delta=delta)

  def _incr(self, entity_group, key, delta=1):
    try:
      old_entry = self._get_entry(entity_group, key)
    except KeyError:
      return None
    if self._gettime() > old_entry.expires_at:
      self._delete(entity_group, key)
      return None
    try:
      old_value = pickle.loads(old_entry.value)
      if isinstance(old_value, str):
        new_value = str(long(old_value) + long(delta))
      else:
        new_value = long(old_value) + long(delta)
    except ValueError:
      return None
    if not self._set_entry(entity_group, key, new_value, old_entry.expires_at):
      return None
    return new_value

  def decr(self, key, delta=1, namespace=None):
    entity_group = self._get_entity_group(namespace)
    return db.run_in_transaction(self._incr, entity_group, key, delta=-delta)

  def flush_all(self):
    for entity_group in CacheNamespace.all().fetch(self._MAX_NAMESPACES):
      db.run_in_transaction(self._flush_all, entity_group)
    return True

  def _flush_all(self, entity_group):
    max = self._MAX_ENTRIES_PER_NAMESPACE
    db.delete(CacheEntry.all().ancestor(entity_group).fetch(max))
    key = self._get_statistics_key(entity_group)
    statistics = db.get(key)
    if statistics:
      statistics.delete()

  def get_stats(self, namespace=None):
    if namespace:
      entity_group = self._get_entity_group(namespace)
      return self._get_stats(entity_group)
    all_stats = list()
    for entity_group in CacheNamespace.all().fetch(self._MAX_NAMESPACES):
      all_stats.append(db.run_in_transaction(self._get_stats, entity_group))
    total_stats = dict(hits=0, misses=0, items=0)
    for namespace_stats in all_stats:
      for key in ['hits', 'misses', 'items']:
        total_stats[key] += namespace_stats.get(key, 0)
    return total_stats

  def _get_cache_statistics(self, entity_group):
    statistics_key = self._get_statistics_key(entity_group)
    statistics = db.get(statistics_key)
    if not statistics:
      statistics = CacheStatistics(key=statistics_key)
    return statistics

  def _incr_misses(self, entity_group, count=1):
    statistics = self._get_cache_statistics(entity_group)
    statistics.misses += count
    statistics.put()

  def _incr_hits(self, entity_group, count=1):
    statistics = self._get_cache_statistics(entity_group)
    statistics.hits += count
    statistics.put()

  def _incr_items(self, entity_group, count=1):
    statistics = self._get_cache_statistics(entity_group)
    statistics.items += count
    statistics.put()

  def _decr_items(self, entity_group, count=1):
    statistics = self._get_cache_statistics(entity_group)
    if statistics.items > 0:
      statistics.items -= count
    statistics.put()

  def _get_stats(self, entity_group):
    statistics_key = self._get_statistics_key(entity_group)
    statistics = db.get(statistics_key)
    if not statistics:
      return dict(hits=0, misses=0, items=0)
    return dict(
      hits=statistics.hits,
      misses=statistics.misses,
      items=statistics.items)
