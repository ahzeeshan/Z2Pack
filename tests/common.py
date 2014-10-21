#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>
# Date:    15.10.2014 10:18:11 CEST
# File:    common.py

import types
import unittest

"""assert functions for all tests"""

def assertIterAlmostEqual(TestCase, x, y, iter_type = list):
    """
    comparing iterables of numbers (float, int) for almost equality
    """
    if not(isinstance(x, iter_type) and isinstance(y, iter_type)):
        unittest.fail(msg = 'type of compared input is not list')
    if not(len(x) == len(y)):
        fail(msg = 'length of objects not equal')

    for i in range(len(x)):
        TestCase.assertAlmostEqual(x[i], y[i])

def assertContainerAlmostEqual(TestCase, x, y):
    """
    comparing two containers (arbitrary depth) for almost equality
    """
    try:
        if not(len(x) == len(y)):
            fail(msg='length of objects not equal')
        for i in range(len(x)):
            TestCase.assertContainerAlmostEqual(x[i], y[i])
    except TypeError:
        TestCase.assertAlmostEqual(x, y)


class CommonTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(CommonTestCase, self).__init__(*args, **kwargs)
        self.assertIterAlmostEqual = types.MethodType(assertIterAlmostEqual, self)
        self.assertContainerAlmostEqual = types.MethodType(
        assertContainerAlmostEqual, self)

if __name__ == "__main__":
    print("common.py")
