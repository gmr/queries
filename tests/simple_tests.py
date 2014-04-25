"""
Queries Simple Method Tests

"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from queries import simple


class URITests(unittest.TestCase):

    def test_uri_without_password(self):
        """Validate URI method without password"""
        expectation = 'pgsql://foo@bar:9999/baz'
        self.assertEqual(simple.uri('bar', 9999, 'baz', 'foo'), expectation)

    def test_uri_with_password(self):
        """Validate URI method with a password"""
        expectation = 'pgsql://foo:bar@baz:9999/qux'
        self.assertEqual(simple.uri('baz', 9999, 'qux', 'foo', 'bar'),
                         expectation)
