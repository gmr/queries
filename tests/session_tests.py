"""
Tests for functionality in the session module

"""
import hashlib
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from psycopg2 import extras
import psycopg2

from queries import pool
from queries import results
from queries import session


class SessionTests(unittest.TestCase):

    URI = 'pgsql://foo:bar@localhost:5432/foo'


    def setUp(self):
        self.conn = mock.Mock()
        self._connect = mock.Mock(return_value=self.conn)
        self.cursor = mock.Mock()
        self._get_cursor = mock.Mock(return_value=self.cursor)
        self._autocommit = mock.Mock()
        with mock.patch.multiple('queries.session.Session',
                                 _connect=self._connect,
                                 _get_cursor=self._get_cursor,
                                 _autocommit=self._autocommit):
            pool.PoolManager.create = self.pm_create = mock.Mock()
            pool.PoolManager.is_full = self.pm_is_full = mock.PropertyMock()
            pool.PoolManager.remove_connection = self.pm_rem_conn = mock.Mock()
            self.obj = session.Session(self.URI)

    def test_init_gets_poolmanager_instance(self):
        instance = pool.PoolManager.instance()
        self.assertEqual(self.obj._pool_manager, instance)

    def test_init_sets_uri(self):
        self.assertEqual(self.obj._uri, self.URI)

    def test_init_invokes_poolmanager_create(self):
        self.obj._pool_manager.create.assert_called_once_with(
            self.obj.pid,
            pool.DEFAULT_IDLE_TTL,
            pool.DEFAULT_MAX_SIZE)

    def test_init_invokes_connection(self):
        self._connect.assert_called_once_with()

    def test_init_sets_cursorfactory(self):
        self.assertEqual(self.obj._cursor_factory, extras.RealDictCursor)

    def test_init_gets_cursor(self):
        self._get_cursor.assert_called_once_with(self.conn)

    def test_init_sets_autocommit(self):
        self._autocommit.assert_called_once_with()

    def test_backend_pid_invokes_conn_backend_pid(self):
        self.conn.get_backend_pid = get_backend_pid = mock.Mock()
        val = self.obj.backend_pid
        get_backend_pid.assert_called_once_with()

    def test_callproc_invokes_cursor_callproc(self):
        self.cursor.callproc = mock.Mock()
        args = ('foo', ['bar', 'baz'])
        self.obj.callproc(*args)
        self.cursor.callproc.assert_called_once_with(*args)

    def test_callproc_returns_results(self):
        self.cursor.callproc = mock.Mock()
        args = ('foo', ['bar', 'baz'])
        self.assertIsInstance(self.obj.callproc(*args), results.Results)

    def test_close_raises_exception(self):
        self.obj._conn = None
        self.assertRaises(psycopg2.InterfaceError, self.obj.close)

    def test_close_removes_connection(self):
        self.obj.close()
        self.pm_rem_conn.assert_called_once_with(self.obj.pid, self.conn)

    def test_close_unassigns_connection(self):
        self.obj.close()
        self.assertIsNone(self.obj._conn)

    def test_close_unassigns_cursor(self):
        self.obj.close()
        self.assertIsNone(self.obj._cursor)

    def test_connection_property_returns_correct_value(self):
        self.assertEqual(self.obj.connection, self.conn)

    def test_cursor_property_returns_correct_value(self):
        self.assertEqual(self.obj.cursor, self.cursor)

    def test_encoding_property_value(self):
        self.conn.encoding = 'UTF-8'
        self.assertEqual(self.obj.encoding, 'UTF-8')

    def test_notices_value(self):
        self.conn.notices = [1, 2, 3]
        self.assertListEqual(self.obj.notices, [1, 2, 3])

    def test_pid_value(self):
        expectation = str(hashlib.md5(self.URI.encode('utf-8')).hexdigest())
        self.assertEqual(self.obj.pid, expectation)

    def test_query_invokes_cursor_execute(self):
        self.cursor.execute = mock.Mock()
        args = ('SELECT * FROM foo', ['bar', 'baz'])
        self.obj.query(*args)
        self.cursor.execute.assert_called_once_with(*args)

    def test_set_encoding_sets_encoding_if_different(self):
        self.conn.encoding = 'LATIN-1'
        self.conn.set_client_encoding = set_client_encoding = mock.Mock()
        self.obj.set_encoding('UTF-8')
        set_client_encoding.assert_called_once_with('UTF-8')

    def test_set_encoding_does_not_set_encoding_if_same(self):
        self.conn.encoding = 'UTF-8'
        self.conn.set_client_encoding = set_client_encoding = mock.Mock()
        self.obj.set_encoding('UTF-8')
        self.assertFalse(set_client_encoding.called)
