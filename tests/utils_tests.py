"""
Tests for functionality in the utils module

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from queries import utils


class GetCurrentUserTests(unittest.TestCase):

    @mock.patch('pwd.getpwuid')
    def test_get_current_user(self, getpwuid):
        """get_current_user returns value from pwd.getpwuid"""
        getpwuid.return_value = ['mocky']
        self.assertEqual(utils.get_current_user(), 'mocky')


class URLParseTestCase(unittest.TestCase):

    URI = 'postgresql://foo:bar@baz:5444/qux'

    def test_urlparse_hostname(self):
        """hostname should match expectation"""
        self.assertEqual(utils.urlparse(self.URI).hostname, 'baz')

    def test_urlparse_port(self):
        """port should match expectation"""
        self.assertEqual(utils.urlparse(self.URI).port, 5444)

    def test_urlparse_path(self):
        """path should match expectation"""
        self.assertEqual(utils.urlparse(self.URI).path, '/qux')

    def test_urlparse_username(self):
        """username should match expectation"""
        self.assertEqual(utils.urlparse(self.URI).username, 'foo')

    def test_urlparse_password(self):
        """password should match expectation"""
        self.assertEqual(utils.urlparse(self.URI).password, 'bar')


class URIToKWargsTestCase(unittest.TestCase):

    URI = ('postgresql://foo:c%23%5E%25%23%27%24%40%3A@baz:5444/qux?'
           'options=foo&options=bar&keepalives=1&invalid=true')

    def test_uri_to_kwargs_host(self):
        """hostname should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['host'], 'baz')

    def test_uri_to_kwargs_port(self):
        """port should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['port'], 5444)

    def test_uri_to_kwargs_dbname(self):
        """dbname should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['dbname'], 'qux')

    def test_uri_to_kwargs_username(self):
        """user should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['user'], 'foo')

    def test_uri_to_kwargs_password(self):
        """password should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['password'],
                         'c#^%#\'$@:')

    def test_uri_to_kwargs_options(self):
        """options should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['options'],
                         ['foo', 'bar'])

    def test_uri_to_kwargs_keepalive(self):
        """keepalive should match expectation"""
        self.assertEqual(utils.uri_to_kwargs(self.URI)['keepalives'], 1)

    def test_uri_to_kwargs_invalid(self):
        """invalid query argument should not be in kwargs"""
        self.assertNotIn('invaid', utils.uri_to_kwargs(self.URI))

    def test_unix_socket_path_format_one(self):
        socket_path = 'postgresql://%2Fvar%2Flib%2Fpostgresql/dbname'
        result = utils.uri_to_kwargs(socket_path)
        self.assertEqual(result['host'], '/var/lib/postgresql')

    def test_unix_socket_path_format2(self):
        socket_path = 'postgresql:///postgres?host=/tmp/'
        result = utils.uri_to_kwargs(socket_path)
        self.assertEqual(result['host'], '/tmp/')


