#!/usr/bin/python2.5
#
# Memory cache functionality.
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

import logging
import sys
import threading
import time

class Client(object):

  _data = dict()
  _lock = threading.Lock()
  _stats = dict(hits=0, misses=0)

  _MAX_EXPIRES_IN = 60 * 60 * 24 * 31
  _NO_EXPIRATION = sys.maxint  # TODO(dewitt): Replace with max long
  _DEFAULT_NAMESPACE = object()

  _DELETE_NETWORK_FAILURE = 0
  _DELETE_ITEM_MISSING = 1
  _DELETE_SUCCESSFUL = 2

  def __init__(self, default_time=_NO_EXPIRATION, gettime=time.time):
    self._gettime = gettime
    self._default_time = default_time

  def set(self, key, value, time=None, min_compress_len=0, namespace=None):
    self._lock.acquire()
    try:
      return self._set(key, value, time=time, namespace=namespace)
    finally:
      self._lock.release()

  def _set(self, key, value, time=None, namespace=None):
    if not time:
      time = self._default_time
    # Compute the expiration time
    if time <= self._MAX_EXPIRES_IN:  # time is a delta in seconds
      expires_at = self._gettime() + time
    else:  # time is seconds since the epoch
      expires_at = time
    # Build and store the entry
    entry = {'value': value, 'expires_at': expires_at}
    return self._set_entry(key, entry, namespace=namespace)

  def _set_entry(self, key, entry, namespace=None):
    if key is None:
      raise ValueError('Invalid key "%s"' % key)
    # Ignore the (hash_value, string) form of keys
    if isinstance(key, tuple):
      key = key[1]
    # Set up the namespace if necessary
    if not namespace:
      namespace = self._DEFAULT_NAMESPACE
    if namespace not in Client._data:
      Client._data[namespace] = dict()
    # Store the entry
    Client._data[namespace][key] = entry
    return True

  def set_multi(self,
                mapping,
                time=None,
                key_prefix='',
                min_compress_len=0,
                namespace=None):
    self._lock.acquire()
    try:
      return self._set_multi(mapping,
                             time=time,
                             key_prefix=key_prefix,
                             namespace=namespace)
    finally:
      self._lock.release()

  def _set_multi(self, mapping, time=None, key_prefix='', namespace=None):
    not_set = list()
    for key, value in mapping.iteritems():
      if not self._set(key_prefix + key, value, time=time, namespace=namespace):
        not_set.append(key)
    return not_set

  def get(self, key, namespace=None):
    self._lock.acquire()
    try:
      return self._get(key, namespace=namespace)
    finally:
      self._lock.release()

  def _get(self, key, namespace=None):
    try:
      entry = self._get_entry(key, namespace=namespace)
    except KeyError:
      self._incr_misses()
      return None
    if self._gettime() > entry['expires_at']:
      self._incr_misses()
      self._delete(key, namespace=namespace)
      return None
    else:
      self._incr_hits()
      return entry['value']

  def _get_entry(self, key, namespace=None):
    """Returns entry, raises KeyError if not found."""
    if key is None:
      raise ValueError('Invalid key "%s"' % key)
    # Ignore the (hash_value, string) form of keys
    if isinstance(key, tuple):
      key = key[1]
    # Set up the namespace if necessary
    if not namespace:
      namespace = self._DEFAULT_NAMESPACE
    # Retrieve the entry and return it, expired or not, raising KeyError
    return Client._data[namespace][key]

  def get_multi(self, keys, key_prefix='', namespace=None):
    self._lock.acquire()
    try:
      return self._get_multi(keys, key_prefix=key_prefix, namespace=namespace)
    finally:
      self._lock.release()

  def _get_multi(self, keys, key_prefix='', namespace=None):
    results = dict()
    for key in keys:
      results[key] = self._get(key_prefix + key, namespace=namespace)
    return results

  def delete(self, key, seconds=0, namespace=None):
    self._lock.acquire()
    try:
      return self._delete(key, seconds=seconds, namespace=namespace)
    finally:
      self._lock.release()

  def _delete(self, key, seconds=0, namespace=None):
    # If we're supposed to block adds for a number of seconds
    if seconds:
      expires_at = self._gettime() + seconds
      self._set(key, None, time=expires_at, namespace=namespace)
    else:
      # Ignore the (hash_value, string) form of keys
      if isinstance(key, tuple):
        key = key[1]
      # Set up the namespace if necessary
      if not namespace:
        namespace = self._DEFAULT_NAMESPACE
      del Client._data[namespace][key]
    return self._DELETE_SUCCESSFUL

  def delete_multi(self, keys, seconds=0, key_prefix='', namespace=None):
    self._lock.acquire()
    try:
      return self._delete_multi(
        keys, key_prefix=key_prefix, seconds=seconds, namespace=namespace)
    finally:
      self._lock.release()

  def _delete_multi(self, keys, seconds=0, key_prefix='', namespace=None):
    statuses = list()
    for key in keys:
      statuses.append(
        self._delete(key_prefix + key, seconds=seconds, namespace=namespace))
    return all(statuses)

  def add(self, key, value, time=0, min_compress_len=0, namespace=None):
    self._lock.acquire()
    try:
      return self._add(key, value, time=time, namespace=namespace)
    finally:
      self._lock.release()

  def _add(self, key, value, time=0, namespace=None):
    try:
      entry = self._get_entry(key, namespace=namespace)
      if self._gettime() <= entry['expires_at']:
        return False  # The extry exist and hasn't expired
      # The entry existed, but has expired, so we can set it again below
    except KeyError:
      pass  # the key doesn't exist, so we can set it
    self._set(key, value, time=time, namespace=namespace)
    return True

  def add_multi(self,
                mapping,
                time=0,
                key_prefix='',
                min_compress_len=0,
                namespace=None):
    self._lock.acquire()
    try:
      return self._add_multi(
        mapping, time=time, key_prefix=key_prefix, namespace=namespace)
    finally:
      self._lock.release()

  def _add_multi(self, mapping, time=0, key_prefix='', namespace=None):
    not_set = list()
    for key, value in mapping.iteritems():
      if not self._add(key_prefix + key, value, time=time, namespace=namespace):
        not_set.append(key)
    return not_set

  def replace(self, key, value, time=0, min_compress_len=0, namespace=None):
    self._lock.acquire()
    try:
      return self._replace(key, value, time=time, namespace=namespace)
    finally:
      self._lock.release()

  def _replace(self, key, value, time=0, namespace=None):
    try:
      entry = self._get_entry(key, namespace=namespace)
      if self._gettime() <= entry['expires_at']:  # Unexpired entries
        self._set(key, value, time=time, namespace=namespace)
        return True
      else:
        self._delete(key, namespace=namespace)  # Delete expired entries
        return False
    except KeyError:
      return False  # the entry doesn't exist, so we can't replace it

  def replace_multi(self,
                    mapping,
                    time=0,
                    key_prefix='',
                    min_compress_len=0,
                    namespace=None):
    self._lock.acquire()
    try:
      return self._replace_multi(
        mapping, time=time, key_prefix=key_prefix, namespace=namespace)
    finally:
      self._lock.release()

  def _replace_multi(self,
                     mapping,
                     time=0,
                     key_prefix='',
                     namespace=None):
    not_set = list()
    for key, value in mapping.iteritems():
      if not self._replace(key_prefix + key, value, time=time, namespace=namespace):
        not_set.append(key)
    return not_set

  def incr(self, key, delta=1, namespace=None):
    self._lock.acquire()
    try:
      return self._incr(key, delta=delta, namespace=namespace)
    finally:
      self._lock.release()

  def _incr(self, key, delta=1, namespace=None):
    try:
      old_entry = self._get_entry(key, namespace=namespace)
    except KeyError:
      return None
    if self._gettime() > old_entry['expires_at']:
      self._delete(key, namespace=namespace)
      return None
    new_entry = old_entry.copy()
    try:
      old_value = old_entry['value']
      if isinstance(old_value, str):
        new_value = str(long(old_value) + long(delta))
      else:
        new_value = long(old_value) + long(delta)
      new_entry['value'] = new_value
    except ValueError:
      return None
    if not self._set_entry(key, new_entry, namespace=namespace):
      return None
    return new_value

  def decr(self, key, delta=1, namespace=None):
    self._lock.acquire()
    try:
      return self._incr(key, delta=-delta, namespace=namespace)
    finally:
      self._lock.release()

  def flush_all(self):
    self._lock.acquire()
    try:
      return self._flush_all()
    finally:
      self._lock.release()

  def _flush_all(self):
    Client._data = dict()
    Client._stats = dict(hits=0, misses=0)
    return True

  def _incr_misses(self, count=1):
    Client._stats['misses'] += count

  def _incr_hits(self, count=1):
    Client._stats['hits'] += count

  def get_stats(self):
    total_items = 0
    for namespace in Client._data:
      total_items = len(Client._data[namespace])
    return dict(Client._stats, items=total_items)
