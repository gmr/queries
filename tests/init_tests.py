"""
Tests for functionality in the __init__.py module

"""
import platform
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from queries import PYPY


class PYPYDetectionTests(unittest.TestCase):

    def test_pypy_flag(self):
        """PYPY flag is set properly"""
        self.assertEqual(PYPY, platform.python_implementation() == 'PyPy')
