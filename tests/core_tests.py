"""
Tests for the core Queries class

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import psycopg2
from psycopg2 import extensions

from queries import core
from queries import pool
from queries import PYPY


class PostgresTests(unittest.TestCase):

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def setUp(self, register_uuid, register_type, connect):
        self._connect = connect
        self._connect.reset = mock.Mock()
        self._reg_type = register_type
        self._reg_uuid = register_uuid
        self.uri = 'pgsql://postgres@127.0.0.1:5432/queries'
        if self.uri in pool.CONNECTIONS:
            del pool.CONNECTIONS[self.uri]
        self.client = core.Postgres(self.uri)

    def test_psycopg2_connection_invoked(self):
        """Ensure that psycopg2.connect was invoked"""
        self._connect.assert_called_once_with(self.uri)

    def test_psycopg2_register_uuid(self):
        """Ensure that the UUID extension was registered"""
        self._reg_uuid.assert_called_once_with(self.client._conn)

    def test_psycopg2_register_unicode_type(self):
        """Ensure that the UNICODE type was registered"""
        self._reg_type.assert_any_call(psycopg2.extensions.UNICODE,
                                       self.client._cursor)

    def test_psycopg2_register_unicode_array_type(self):
        """Ensure that the UNICODEARRAY type was registered"""
        self._reg_type.assert_any_call(psycopg2.extensions.UNICODEARRAY,
                                       self.client._cursor)

    def test_default_autocommit_value(self):
        """Connection should be autocommit by default"""
        self.assertTrue(self.client._conn.autocommit)

    def test_connection_property(self):
        """Test value of Postgres.connection property"""
        self.assertEqual(self.client._conn, self.client.connection)

    def test_cursor_property(self):
        """Test value of Postgres.connection property"""
        self.assertEqual(self.client._cursor, self.client.cursor)

    def test_connection_added_to_cache(self):
        """Ensure the connection is in the connection cache"""
        self.assertIn(self.uri, pool.CONNECTIONS)

    def test_connection_handle_in_cache(self):
        """Ensure that the connection handle in cache is valid"""
        self.assertEqual(pool.CONNECTIONS[self.uri]['handle'],
                         self.client._conn)

    def test_cleanup_removes_client_from_cache(self):
        """Ensure that Postgres._cleanup frees the client in the cache"""
        value = pool.CONNECTIONS[self.uri]['clients']
        self.client._cleanup()
        self.assertEqual(pool.CONNECTIONS[self.uri]['clients'], value - 1)

    @unittest.skipIf(not PYPY, 'PyPy only test')
    def test_conn_reset_if_pypy(self):
        """Connection reset should be called when using PyPy"""
        self.client._conn.reset.assert_called_once_with()

    @unittest.skipIf(PYPY, 'Not invoked in PyPy')
    def test_del_invokes_cleanup(self):
        """Deleting Postgres instance invokes Postgres._cleanup"""
        with mock.patch('queries.core.Postgres._cleanup') as cleanup:
            del self.client
            cleanup.assert_called_once_with()

    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_context_manager_creation(self, _reg_uuid, _reg_type):
        """Ensure context manager returns self"""
        with core.Postgres(self.uri) as conn:
            self.assertIsInstance(conn, core.Postgres)

    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_context_manager_cleanup(self, _reg_uuid, _reg_type):
        """Ensure context manager cleans up after self"""
        with mock.patch('queries.core.Postgres._cleanup') as cleanup:
            with core.Postgres(self.uri):
                pass
        cleanup.assert_called_with()

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_removes_from_cache(self, _reg_uuid, _reg_type, _connect):
        """Ensure connection removed from cache on close"""
        uri = 'pgsql://foo@bar:9999/baz'
        pgsql = core.Postgres(uri)
        self.assertIn(uri, pool.CONNECTIONS)
        pgsql.close()
        self.assertNotIn(uri, pool.CONNECTIONS)

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_invokes_connection_close(self, _reg_uuid, _reg_type, connect):
        """Ensure close calls connection.close"""
        conn = core.Postgres('pgsql://foo@bar:9999/baz')
        close_mock = mock.Mock()
        conn._conn.close = close_mock
        conn.close()
        close_mock .assert_called_once_with()

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_sets_conn_to_none(self, _reg_uuid, _reg_type, connect):
        """Ensure Postgres._conn is None after close"""
        conn = core.Postgres('pgsql://foo@bar:9999/baz')
        conn.close()
        self.assertIsNone(conn._conn)

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_sets_cursor_to_none(self, _reg_uuid, _reg_type, connect):
        """Ensure Postgres._cursor is None after close"""
        conn = core.Postgres('pgsql://foo@bar:9999/baz')
        conn.close()
        self.assertIsNone(conn._cursor)

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_close_raises_when_closed(self, _reg_uuid, _reg_type, _conn):
        """Ensure Postgres._cursor is None after close"""
        conn = core.Postgres('pgsql://foo@bar:9999/baz')
        conn.close()
        self.assertRaises(AssertionError, conn.close)
