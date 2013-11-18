# -*- coding: utf-8 -*-

import re
import operator
from collections import OrderedDict


P_EXP = ur'(?P<sign>[+-])(?P<title>.+?)(?=\s$|\s[+-])'


def parse_expression(exp):
    exp = exp.strip() + ' '
    positives = []
    negatives = []

    for m in re.finditer(P_EXP, exp):
        sign = m.group('sign')
        title = m.group('title')
        if sign == '+':
            positives.append(title)
        else:
            negatives.append(title)

    return {
        'pos': positives,
        'neg': negatives,
    }


def evaluate(positives, negatives):
    scoretable = {}
    length = len(positives.keys()) + len(negatives.keys())

    # calc positives
    for scores in positives.values():
        for title, score in scores.items():
            if title not in scoretable:
                scoretable[title] = 0.0
            scoretable[title] += score / length

    # calc negatives
    for scores in negatives.values():
        for title, score in scores.items():
            if title not in scoretable:
                scoretable[title] = 0.0
            scoretable[title] -= score / length

    # descending by score
    sorted_tuples = sorted(scoretable.iteritems(),
                           key=operator.itemgetter(1),
                           reverse=True)

    return OrderedDict(sorted_tuples)
