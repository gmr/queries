"""
Tests for the session.Session class

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import psycopg2
from psycopg2 import extensions

from queries import session
from queries import pool
from queries import PYPY


class SessionTests(unittest.TestCase):

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def setUp(self, register_uuid, register_json, register_type, connect):
        self._connect = connect
        self._connect.reset = mock.Mock()
        self._reg_json = register_json
        self._reg_type = register_type
        self._reg_uuid = register_uuid
        self.uri = 'pgsql://postgres@127.0.0.1:5432/queries'
        if self.uri in pool.CONNECTIONS:
            del pool.CONNECTIONS[self.uri]
        self.client = session.Session(self.uri)

    def test_psycopg2_connection_invoked(self):
        """Ensure that psycopg2.connect was invoked"""
        expectation = {'user': 'postgres',
                       'dbname': 'queries',
                       'host': '127.0.0.1',
                       'port': 5432,
                       'password': None}
        self._connect.assert_called_once_with(**expectation)

    def test_psycopg2_register_json(self):
        """Ensure that the JSON extension was registered"""
        self._reg_json.assert_called_once_with(conn_or_curs=self.client._conn)

    def test_psycopg2_register_uuid(self):
        """Ensure that the UUID extension was registered"""
        self._reg_uuid.assert_called_once_with(conn_or_curs=self.client._conn)

    def test_psycopg2_register_unicode_type(self):
        """Ensure that the UNICODE type was registered"""
        self._reg_type.assert_any_call(psycopg2.extensions.UNICODE,
                                       self.client._conn)

    def test_psycopg2_register_unicode_array_type(self):
        """Ensure that the UNICODEARRAY type was registered"""
        self._reg_type.assert_any_call(psycopg2.extensions.UNICODEARRAY,
                                       self.client._conn)

    def test_default_autocommit_value(self):
        """Connection should be autocommit by default"""
        self.assertTrue(self.client._conn.autocommit)

    def test_connection_property(self):
        """Test value of Session.connection property"""
        self.assertEqual(self.client._conn, self.client.connection)

    def test_cursor_property(self):
        """Test value of Session.connection property"""
        self.assertEqual(self.client._cursor, self.client.cursor)

    def test_connection_added_to_cache(self):
        """Ensure the connection is in the connection cache"""
        self.assertIn(self.uri, pool.CONNECTIONS)

    def test_connection_handle_in_cache(self):
        """Ensure that the connection handle in cache is valid"""
        self.assertEqual(pool.CONNECTIONS[self.uri]['handle'],
                         self.client._conn)

    def test_cleanup_removes_client_from_cache(self):
        """Ensure that Session._cleanup frees the client in the cache"""
        value = pool.CONNECTIONS[self.uri]['clients']
        self.client._cleanup()
        self.assertEqual(pool.CONNECTIONS[self.uri]['clients'], value - 1)

    @unittest.skipIf(not PYPY, 'PyPy only test')
    def test_conn_reset_if_pypy(self):
        """Connection reset should be called when using PyPy"""
        self.client._conn.reset.assert_called_once_with()

    @unittest.skipIf(PYPY, 'Not invoked in PyPy')
    def test_del_invokes_cleanup(self):
        """Deleting Session instance invokes Session._cleanup"""
        with mock.patch('queries.session.Session._cleanup') as cleanup:
            del self.client
            cleanup.assert_called_once_with()

    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_context_manager_creation(self, _uuid, _json, _type,):
        """Ensure context manager returns self"""
        with session.Session(self.uri) as conn:
            self.assertIsInstance(conn, session.Session)

    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_context_manager_cleanup(self, _uuid, _json, _type,):
        """Ensure context manager cleans up after self"""
        with mock.patch('queries.session.Session._cleanup') as cleanup:
            with session.Session(self.uri):
                pass
        cleanup.assert_called_with()

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_removes_from_cache(self, _uuid, _json, _type, _connect):
        """Ensure connection removed from cache on close"""
        uri = 'pgsql://foo@bar:9999/baz'
        pgsql = session.Session(uri)
        self.assertIn(uri, pool.CONNECTIONS)
        pgsql.close()
        self.assertNotIn(uri, pool.CONNECTIONS)

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_invokes_connection_close(self, _uuid, _json, _type, connect):
        """Ensure close calls connection.close"""
        sess = session.Session('pgsql://foo@bar:9999/baz')
        close_mock = mock.Mock()
        sess._conn.close = close_mock
        sess.close()
        close_mock .assert_called_once_with()

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_sets_conn_to_none(self, _uuid, _json, _type, connect):
        """Ensure Session._conn is None after close"""
        sess = session.Session('pgsql://foo@bar:9999/baz')
        sess.close()
        self.assertIsNone(sess._conn)

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_sets_cursor_to_none(self, _uuid, _json, _type, connect):
        """Ensure Session._cursor is None after close"""
        sess = session.Session('pgsql://foo@bar:9999/baz')
        sess.close()
        self.assertIsNone(sess._cursor)

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extras.register_json')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_raises_when_closed(self, _uuid, _json, _type, _conn):
        """Ensure Session._cursor is None after close"""
        sess = session.Session('pgsql://foo@bar:9999/baz')
        sess.close()
        self.assertRaises(AssertionError, sess.close)
