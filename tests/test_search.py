# -*- coding: utf-8 -*-
import search
import unittest2 as unittest


class ExpressionParserTest(unittest.TestCase):
    def test_single_title(self):
        expected = {
            'pos': [u'Hello'],
            'neg': [],
        }
        actual = search.parse_expression(u'+Hello')
        self.assertEqual(expected, actual)

    def test_multiple_titles(self):
        expected = {
            'pos': [u'What the', u'Is it'],
            'neg': [u'Fun'],
        }
        actual = search.parse_expression(u'+What the -Fun +Is it')
        self.assertEqual(expected, actual)

    def test_no_space(self):
        expected = {
            'pos': [u'User-centered design'],
            'neg': [],
        }
        actual = search.parse_expression(u'+User-centered design')
        self.assertEqual(expected, actual)


class EvaluationTest(unittest.TestCase):
    def test_should_not_contain_self(self):
        positives = {
            u'A': {
                u'A': 0.2,
                u'B': 0.2,
                u'C': 0.3,
            },
            u'B': {
                u'B': 0.2,
                u'C': 0.2,
                u'D': 0.2,
            }
        }
        negatives = {
            u'C': {
                u'A': 0.2,
                u'E': 0.1,
            }
        }

        expected = [u'D', u'E']
        actual = search.evaluate(positives, negatives).keys()
        self.assertEqual(expected, actual)

    def test_complex_case(self):
        positives = {
            u'Page 1': {
                u'A': 0.2,
                u'B': 0.2,
                u'C': 0.3,
            },
            u'Page 2': {
                u'B': 0.2,
                u'C': 0.2,
                u'D': 0.2,
            }
        }
        negatives = {
            u'Page 3': {
                u'A': 0.2,
                u'E': 0.1,
            }
        }

        expected = [u'C', u'B', u'D', u'A', u'E']
        actual = search.evaluate(positives, negatives).keys()
        self.assertEqual(expected, actual)
