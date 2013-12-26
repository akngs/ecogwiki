#!/usr/bin/python2.5
#
# A multi-tiered layered cache wrapper.
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


class NotImplementedException(Exception):
  pass

class Client(object):

  _caches = None

  def __init__(self, caches, *args, **kwargs):
    """Construct a new multi-tiered layered cache.

    Args:
      caches -- A list of one or more caches, from fastest to slowest
    """
    self._caches = caches

  def _until(self, iterable, predicate):
    """Return the first element that matches the predicate, otherwise the last."""
    for i in iterable:
      if predicate(i):
        return i
    return i

  def set(self, *args, **kwargs):
    return self._until(
      (cache.set(*args, **kwargs) for cache in self._caches),
      lambda x : x is not True)

  def set_multi(self, *args, **kwargs):
    return self._until(
      (cache.set_multi(*args, **kwargs) for cache in self._caches),
      lambda x : x is not [])

  def get(self, *args, **kwargs):
    prev_cache = None
    for cache in self._caches:
        value = cache.get(*args, **kwargs)
        if value is not None:
            if prev_cache is not None:
                prev_cache.set(args[0], value)
            return value
        prev_cache = cache
    return None

  def get_multi(self, *args, **kwargs):
    # TODO(dewitt): Consider returning an aggregate get that spans tiers
    return self._until(
      (cache.get_multi(*args, **kwargs) for cache in self._caches),
      lambda x : x is not [])

  def delete(self, *args, **kwargs):
    return self._until(
      (cache.delete(*args, **kwargs) for cache in self._caches),
      lambda x : x is None)

  def delete_multi(self, *args, **kwargs):
    return self._until(
      (cache.delete_multi(*args, **kwargs) for cache in self._caches),
      lambda x : x is 0)

  def add(self, *args, **kwargs):
    return self._until(
      (cache.add(*args, **kwargs) for cache in self._caches),
      lambda x : x is not True)

  def add_multi(self, *args, **kwargs):
    return self._until(
      (cache.add_multi(*args, **kwargs) for cache in self._caches),
      lambda x : x is not [])

  def replace(self, *args, **kwargs):
    return self._until(
      (cache.replace(*args, **kwargs) for cache in self._caches),
      lambda x : x is not True)

  def replace_multi(self, *args, **kwargs):
    return self._until(
      (cache.replace_multi(*args, **kwargs) for cache in self._caches),
      lambda x : x is not [])

  def incr(self, *args, **kwargs):
    return self._until(
      (cache.incr(*args, **kwargs) for cache in self._caches),
      lambda x : x is None)

  def decr(self, *args, **kwargs):
    return self._until(
      (cache.decr(*args, **kwargs) for cache in self._caches),
      lambda x : x is None)

  def flush_all(self, *args, **kwargs):
    return self._until(
      (cache.flush_all(*args, **kwargs) for cache in self._caches),
      lambda x : x is not True)

  def get_stats(self):
    raise NotImplementedException()

