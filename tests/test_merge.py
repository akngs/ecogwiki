# -*- coding: utf-8 -*-
import unittest2 as unittest
from bzrlib.merge3 import Merge3


class MergeTest(unittest.TestCase):
    def test_simple_merge(self):
        base = ['a', 'b', 'c']
        # append d
        a = ['a', 'b', 'c', 'd']
        # remove b
        b = ['a', 'c']

        m3 = Merge3(base, a, b)
        self.assertEqual(['a', 'c', 'd'], list(m3.merge_lines()))

    def test_conflict(self):
        base = ['a', 'b', 'c']
        # b -> b1
        a = ['a', 'b1', 'c']
        # b -> b2
        b = ['a', 'b2', 'c']

        m3 = Merge3(base, a, b)
        self.assertEqual(['a', '<<<<<<<\n', 'b1', '=======\n', 'b2', '>>>>>>>\n', 'c'], list(m3.merge_lines()))
