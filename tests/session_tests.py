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

from queries import PYPY


class SessionTestCase(unittest.TestCase):

    URI = 'pgsql://foo:bar@localhost:5432/foo'

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    @mock.patch('queries.utils.uri_to_kwargs')
    def setUp(self, uri_to_kwargs, register_uuid, register_type, connect):
        self.conn = mock.Mock()
        self.conn.autocommit = False
        self.conn.closed = False
        self.conn.cursor = mock.Mock()
        self.conn.isexecuting = mock.Mock(return_value=False)
        self.conn.reset = mock.Mock()
        self.conn.status = psycopg2.extensions.STATUS_BEGIN
        self.psycopg2_connect = connect
        self.psycopg2_connect.return_value = self.conn
        self.psycopg2_register_type = register_type
        self.psycopg2_register_uuid = register_uuid

        self.uri_to_kwargs = uri_to_kwargs
        self.uri_to_kwargs.return_value = {'host': 'localhost',
                                           'port': 5432,
                                           'user': 'foo',
                                           'password': 'bar',
                                           'dbname': 'foo'}

        self.obj = session.Session(self.URI)

    def test_init_sets_uri(self):
        self.assertEqual(self.obj._uri, self.URI)

    def test_init_creates_new_pool(self):
        self.assertIn(self.obj.pid, self.obj._pool_manager)

    def test_init_creates_connection(self):
        conns = \
            [value.handle for key, value in
             self.obj._pool_manager._pools[self.obj.pid].connections.items()]
        self.assertIn(self.conn, conns)

    def test_init_sets_cursorfactory(self):
        self.assertEqual(self.obj._cursor_factory, extras.RealDictCursor)

    def test_init_gets_cursor(self):
        self.conn.cursor.assert_called_once_with(
            name=None, cursor_factory=extras.RealDictCursor)

    def test_init_sets_autocommit(self):
        self.assertTrue(self.conn.autocommit)

    def test_backend_pid_invokes_conn_backend_pid(self):
        self.conn.get_backend_pid = get_backend_pid = mock.Mock()
        val = self.obj.backend_pid
        get_backend_pid.assert_called_once_with()

    def test_callproc_invokes_cursor_callproc(self):
        self.obj._cursor.callproc = mock.Mock()
        args = ('foo', ['bar', 'baz'])
        self.obj.callproc(*args)
        self.obj._cursor.callproc.assert_called_once_with(*args)

    def test_callproc_returns_results(self):
        self.obj._cursor.callproc = mock.Mock()
        args = ('foo', ['bar', 'baz'])
        self.assertIsInstance(self.obj.callproc(*args), results.Results)

    def test_close_raises_exception(self):
        self.obj._conn = None
        self.assertRaises(psycopg2.InterfaceError, self.obj.close)

    def test_close_removes_connection(self):
        self.obj.close()
        self.assertNotIn(self.conn,
                         self.obj._pool_manager._pools[self.obj.pid])

    def test_close_unassigns_connection(self):
        self.obj.close()
        self.assertIsNone(self.obj._conn)

    def test_close_unassigns_cursor(self):
        self.obj.close()
        self.assertIsNone(self.obj._cursor)

    def test_connection_property_returns_correct_value(self):
        self.assertEqual(self.obj.connection, self.conn)

    def test_cursor_property_returns_correct_value(self):
        self.assertEqual(self.obj.cursor, self.obj._cursor)

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
        self.obj._cursor.callproc = mock.Mock()
        args = ('SELECT * FROM foo', ['bar', 'baz'])
        self.obj.query(*args)
        self.obj._cursor.execute.assert_called_once_with(*args)

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

    @unittest.skipIf(PYPY, 'PYPY does not invoke object.__del__ synchronously')
    def test_del_invokes_cleanup(self):
        cleanup = mock.Mock()
        with mock.patch.multiple('queries.session.Session',
                                 _cleanup=cleanup,
                                 _connect=mock.Mock(),
                                 _get_cursor=mock.Mock(),
                                 _autocommit=mock.Mock()):
            obj = session.Session(self.URI)
            del obj
            cleanup.assert_called_once_with()

    def test_exit_invokes_cleanup(self):
        cleanup = mock.Mock()
        with mock.patch.multiple('queries.session.Session',
                                 _cleanup=cleanup,
                                 _connect=mock.Mock(),
                                 _get_cursor=mock.Mock(),
                                 _autocommit=mock.Mock()):
            with session.Session(self.URI) as sess:
                pass
            cleanup.assert_called_once_with()

    def test_autocommit_sets_attribute(self):
        self.conn.autocommit = False
        self.obj._autocommit()
        self.assertTrue(self.conn.autocommit)

    def test_cleanup_closes_cursor(self):
        self.obj._cursor.close = closeit = mock.Mock()
        self.conn = None
        self.obj._cleanup()
        closeit.assert_called_once_with()

    def test_cleanup_sets_cursor_to_none(self):
        self.obj._cursor.close = mock.Mock()
        self.conn = None
        self.obj._cleanup()
        self.assertIsNone(self.obj._cursor)

    def test_cleanup_frees_connection(self):
        with mock.patch.object(self.obj._pool_manager, 'free') as free:
            conn = self.obj._conn
            self.obj._cleanup()
            free.assert_called_once_with(self.obj.pid, conn)

    def test_cleanup_sets_connect_to_none(self):
        self.obj._cleanup()
        self.assertIsNone(self.obj._conn)

    def test_cleanup_cleans_pool_manager(self):
        pool.PoolManager.clean = clean = mock.Mock()
        self.obj._cleanup()
        clean.assert_called_once_with(self.obj.pid)

    def test_connect_invokes_pool_manager_get(self):
        with mock.patch.object(self.obj._pool_manager, 'get') as get:
            self.obj._connect()
            get.assert_called_once_with(self.obj.pid, self.obj)

    def test_connect_raises_noidleconnectionserror(self):
        with mock.patch.object(self.obj._pool_manager, 'get') as get:
            with mock.patch.object(self.obj._pool_manager, 'is_full') as full:
                get.side_effect = pool.NoIdleConnectionsError(self.obj.pid)
                full.return_value = True
                self.assertRaises(pool.NoIdleConnectionsError,
                                  self.obj._connect)

    def test_connect_invokes_uri_to_kwargs(self):
        self.uri_to_kwargs.assert_called_once_with(self.URI)

    def test_connect_returned_the_proper_value(self):
        self.assertEqual(self.obj.connection, self.conn)

    def test_status_is_ready_by_default(self):
        self.assertEqual(self.obj._status, self.obj.READY)

    def test_status_when_not_ready(self):
        self.conn.status = self.obj.SETUP
        self.assertEqual(self.obj._status, self.obj.SETUP)

    def test_get_named_cursor_sets_scrollable(self):
        result = self.obj._get_cursor(self.obj._conn, 'test1')
        self.assertTrue(result.scrollable)

    def test_get_named_cursor_sets_withhold(self):
        result = self.obj._get_cursor(self.obj._conn, 'test2')
        self.assertTrue(result.withhhold)

    @unittest.skipUnless(PYPY, 'connection.reset is PYPY only behavior')
    def test_connection_reset_in_pypy(self):
        self.conn.reset.assert_called_once_with()
