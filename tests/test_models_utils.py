# -*- coding: utf-8 -*-
from unittest2 import TestCase
from models.utils import merge_dicts, pairs_to_dict


class PairsToDictTest(TestCase):
    def test_empty(self):
        self.assertEqual({}, pairs_to_dict([]))

    def test_normal_pairs(self):
        self.assertEqual({'a': 1, 'b': 2}, pairs_to_dict([('a', 1), ('b', 2)]))

    def test_duplicated_key(self):
        self.assertEqual({'a': [1, 2]}, pairs_to_dict([('a', 1), ('a', 2)]))

    def test_duplicated_key_and_value(self):
        self.assertEqual({'a': 1}, pairs_to_dict([('a', 1), ('a', 1)]))


class MergeDictTest(TestCase):
    def test_empty(self):
        self.assertEqual({}, merge_dicts([]))

    def test_single_dict(self):
        self.assertEqual({'a': 1}, merge_dicts([{'a': 1}]))

    def test_merge_two(self):
        self.assertEqual({'a': 1, 'b': 2, 'c': 3},
                         merge_dicts([{'a': 1}, {'b': 2, 'c': 3}]))

    def test_merge_two_with_conflict_keys(self):
        self.assertEqual({'a': 1, 'b': [2, 3], 'c': 4},
                         merge_dicts([{'a': 1, 'b': 2}, {'b': 3, 'c': 4}]))

    def test_merge_list_with_scalar(self):
        self.assertEqual({'a': [1, 2, 3]},
                         merge_dicts([{'a': 1}, {'a': [2, 3]}]))

    def test_merge_list_with_list(self):
        self.assertEqual({'a': [1, 2, 3, 4]},
                         merge_dicts([{'a': [1, 2]}, {'a': [3, 4]}]))

    def test_duplicated_value(self):
        self.assertEqual({'a': [1, 2, 3], 'b': 4, 'c': [5, 6]},
                         merge_dicts([{'a': [1, 2], 'b': 4, 'c': [5, 6]}, {'a': [2, 3], 'b': 4, 'c': 5}]))
