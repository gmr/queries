"""
Tests for functionality in the __init__.py module

"""
import platform
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import queries


class PYPYDetectionTests(unittest.TestCase):

    def test_pypy_flag(self):
        """PYPY flag is set properly"""
        self.assertEqual(queries.PYPY,
                         platform.python_implementation() == 'PyPy')


class URICreationTests(unittest.TestCase):

    def test_uri_with_password(self):
        expectation = 'pgsql://foo:bar@baz:5433/qux'
        self.assertEqual(queries.uri('baz', 5433, 'qux', 'foo', 'bar'),
                         expectation)

    def test_uri_without_password(self):
        expectation = 'pgsql://foo@baz:5433/qux'
        self.assertEqual(queries.uri('baz', 5433, 'qux', 'foo'),
                         expectation)

    def test_default_uri(self):
        expectation = 'pgsql://postgres@localhost:5432/postgres'
        self.assertEqual(queries.uri(), expectation)

