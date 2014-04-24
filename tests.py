"""
Tests for the pgsql_wrapper module

"""
import mock
import platform
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

target = platform.python_implementation()
if target == 'PyPy':
    from psycopg2ct import compat
    compat.register()
    PYPY = True

# Import psycopg2 and it's extensions and extras
import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

import pgsql_wrapper


class PYPYDetectionTests(unittest.TestCase):

    def test_pypy_flag(self):
        """PYPY flag is set properly"""
        self.assertEquals(pgsql_wrapper.PYPY, target == 'PyPy')


class ConnectionCachingTests(unittest.TestCase):

    def setUp(self):
        pgsql_wrapper._add_cached_connection('cc0', self.__class__)

    def tearDown(self):
        for key in ['cc0', 'cc1', 'cc2', 'cc3', 'cc4']:
            if key in pgsql_wrapper.CONNECTIONS:
                del pgsql_wrapper.CONNECTIONS[key]

    def test_generate_hash(self):
        """DSN hash generation yields expected value"""
        value = 'host=localhost port=5432 user=postgres dbname=postgres'
        expectation = '14ccea097ebbee7cb15c18ab4c8fdcc875ed8e6a'
        self.assertEqual(pgsql_wrapper._generate_connection_hash(value),
                         expectation)

    def test_add_cached_connection_adds_value(self):
        """Cconnection should already exist in the connection cache"""
        self.assertIn('cc0', pgsql_wrapper.CONNECTIONS)

    def test_get_cached_connection_returns_proper_value(self):
        """Fetching cached connection returns proper value"""
        self.assertEqual(pgsql_wrapper._get_cached_connection('cc0'),
                         self.__class__)

    def test_get_cached_connection_increments_counter(self):
        """Fetching cached connection increments client counter"""
        value = pgsql_wrapper.CONNECTIONS.get('cc0', {}).get('clients', 0)
        pgsql_wrapper._get_cached_connection('cc0')
        self.assertEqual(pgsql_wrapper.CONNECTIONS['cc0']['clients'],
                         value + 1)

    def test_add_cached_connection_new(self):
        """Adding a new connection to module cache returns True"""
        self.assertTrue(pgsql_wrapper._add_cached_connection('cc1', True))

    def test_add_cached_connection_existing(self):
        """Adding an existing connection to module cache returns False"""
        pgsql_wrapper._add_cached_connection('cc2', True)
        self.assertFalse(pgsql_wrapper._add_cached_connection('cc2', True))

    def test_new_then_freed_cached_connection_has_no_clients(self):
        """Freeing connection with one client should decrement counter"""
        pgsql_wrapper._add_cached_connection('cc3', True)
        pgsql_wrapper._free_cached_connection('cc3')
        self.assertEqual(pgsql_wrapper.CONNECTIONS['cc3']['clients'], 0)

    def test_free_cached_connection(self):
        """Freeing connection should update last timestamp"""
        pgsql_wrapper._add_cached_connection('cc4', True)
        pgsql_wrapper._free_cached_connection('cc4')
        self.assertAlmostEqual(pgsql_wrapper.CONNECTIONS['cc4']['last_client'],
                               int(time.time()))

    def test_remove_cached_connection(self):
        """Freeing connection should update last timestamp"""
        pgsql_wrapper._add_cached_connection('cc5', True)
        pgsql_wrapper._remove_cached_connection('cc5')
        self.assertNotIn('cc5', pgsql_wrapper.CONNECTIONS)


class ConnectionCacheExpirationTests(unittest.TestCase):

    def setUp(self):
        pgsql_wrapper._add_cached_connection('cce_test', self.__class__)

    def test_cache_expiration(self):
        """Check that unused connection expires"""
        return_value = time.time() - pgsql_wrapper.CACHE_TTL - 1
        with mock.patch('time.time') as ptime:
            ptime.return_value = return_value
            pgsql_wrapper._free_cached_connection('cce_test')
        pgsql_wrapper._check_for_unused_expired_connections()
        self.assertNotIn('cce_test', pgsql_wrapper.CONNECTIONS)


class PgSQLTests(unittest.TestCase):

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def setUp(self, register_uuid, register_type, connect):
        self._connect = connect
        self._connect.reset = mock.Mock()
        self._reg_type = register_type
        self._reg_uuid = register_uuid
        self.dsn = pgsql_wrapper.PgSQL._get_dsn('127.0.0.1', 5432,
                                                'PgSQLTests',
                                                'postgres', None)
        self.dsn_hash = pgsql_wrapper._generate_connection_hash(self.dsn)
        if self.dsn_hash in pgsql_wrapper.CONNECTIONS:
            del pgsql_wrapper.CONNECTIONS[self.dsn_hash]
        self.client = pgsql_wrapper.PgSQL(host="127.0.0.1",
                                          dbname="PgSQLTests")

    def test_psycopg2_connection_invoked(self):
        """Ensure that psycopg2.connect was invoked"""
        self._connect.assert_called_once_with(self.client._dsn)

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
        """Test value of PgSQL.connection property"""
        self.assertEqual(self.client._conn, self.client.connection)

    def test_cursor_property(self):
        """Test value of PgSQL.connection property"""
        self.assertEqual(self.client._cursor, self.client.cursor)

    def test_connection_added_to_cache(self):
        """Ensure the connection is in the connection cache"""
        self.assertIn(self.dsn_hash, pgsql_wrapper.CONNECTIONS)

    def test_connection_handle_in_cache(self):
        """Ensure that the connection handle in cache is valid"""
        self.assertEqual(pgsql_wrapper.CONNECTIONS[self.dsn_hash]['handle'],
                         self.client._conn)

    def test_cleanup_removes_client_from_cache(self):
        """Ensure that PgSQL._cleanup frees the client in the cache"""
        value = pgsql_wrapper.CONNECTIONS[self.dsn_hash]['clients']
        self.client._cleanup()
        self.assertEqual(pgsql_wrapper.CONNECTIONS[self.dsn_hash]['clients'],
                         value - 1)

    def test_get_dsn_with_password(self):
        """Test when invoking _get_dsn with a password"""
        host, port, dbname, user, pwd = 'foo', 5432, 'bar', 'baz', 'qux'
        self.assertEqual(self.client._get_dsn(host, port, dbname, user, pwd),
                         ("host='foo' port=5432 dbname='bar' "
                          "user='baz' password='qux'"))

    @unittest.skipIf(target != 'PyPy', 'PyPy only test')
    def test_conn_reset_if_pypy(self):
        """Connection reset should be called when using PyPy"""
        self.client._conn.reset.assert_called_once_with()

    def test_del_invokes_cleanup(self):
        """Deleting PgSQL instance invokes PgSQL._cleanup"""
        with mock.patch('pgsql_wrapper.PgSQL._cleanup') as cleanup:
            del self.client
            cleanup.assert_called_once_with()

    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_context_manager_creation(self, _reg_uuid, _reg_type):
        """Ensure context manager returns self"""
        with pgsql_wrapper.PgSQL(host="127.0.0.1",
                                 dbname="PgSQLTests") as conn:
            self.assertIsInstance(conn, pgsql_wrapper.PgSQL)

    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    def test_context_manager_cleanup(self, _reg_uuid, _reg_type):
        """Ensure context manager cleans up after self"""
        with mock.patch('pgsql_wrapper.PgSQL._cleanup') as cleanup:
            with pgsql_wrapper.PgSQL(host="127.0.0.1",
                                     dbname="PgSQLTests"):
                pass
        cleanup.assert_called_with()
