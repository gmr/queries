"""
Tests for functionality in the tornado_session module

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from psycopg2 import extras

from tornado import concurrent
from tornado import gen
from tornado import ioloop
from tornado import testing

from queries import pool
from queries import tornado_session


class ResultsTests(unittest.TestCase):

    def setUp(self):
        self.cursor = mock.Mock()
        self.fd = 10
        self.cleanup = mock.Mock()
        self.obj = tornado_session.Results(self.cursor, self.cleanup, self.fd)

    def test_cursor_is_assigned(self):
        self.assertEqual(self.obj.cursor, self.cursor)

    def test_fd_is_assigned(self):
        self.assertEqual(self.obj._fd, self.fd)

    def test_cleanup_is_assigned(self):
        self.assertEqual(self.obj._cleanup, self.cleanup)

    @gen.coroutine
    def test_free_invokes_cleanup(self):
        yield self.obj.free()
        self.cleanup.assert_called_once_with(self.cursor, self.fd)


class SessionInitTests(unittest.TestCase):

    def setUp(self):
        self.obj = tornado_session.TornadoSession()

    def test_creates_empty_callback_dict(self):
        self.assertDictEqual(self.obj._futures, {})

    def test_creates_empty_connections_dict(self):
        self.assertDictEqual(self.obj._connections, {})

    def test_sets_default_cursor_factory(self):
        self.assertEqual(self.obj._cursor_factory, extras.RealDictCursor)

    def test_sets_tornado_ioloop_instance(self):
        self.assertEqual(self.obj._ioloop, ioloop.IOLoop.instance())

    def test_sets_poolmananger_instance(self):
        self.assertEqual(self.obj._pool_manager, pool.PoolManager.instance())

    def test_sets_uri(self):
        self.assertEqual(self.obj._uri, tornado_session.DEFAULT_URI)

    def test_creates_pool_in_manager(self):
        self.assertIn(self.obj.pid, self.obj._pool_manager._pools)

    def test_connection_is_none(self):
        self.assertIsNone(self.obj.connection)

    def test_cursor_is_none(self):
        self.assertIsNone(self.obj.cursor)


class SessionConnectTests(testing.AsyncTestCase):

    def setUp(self):
        super(SessionConnectTests, self).setUp()
        self.conn = mock.Mock()
        self.conn.fileno = mock.Mock(return_value=10)
        self.obj = tornado_session.TornadoSession(io_loop=self.io_loop)

        def create_connection(future):
            future.set_result(self.conn)

        self.obj._create_connection = create_connection

    @testing.gen_test
    def test_connect_returns_new_connection(self):
        conn = yield self.obj._connect()
        self.assertEqual(conn, self.conn)

    @testing.gen_test
    def test_connect_returns_pooled_connection(self):
        conn = yield self.obj._connect()
        self.obj._pool_manager.add(self.obj.pid, conn)
        second_result = yield self.obj._connect()
        self.assertEqual(second_result, conn)

    @testing.gen_test
    def test_connect_gets_pooled_connection(self):
        conn = yield self.obj._connect()
        self.obj._pool_manager.add(self.obj.pid, conn)
        with mock.patch.object(self.obj._pool_manager, 'get') as get:
            with mock.patch.object(self.io_loop, 'add_handler'):
                yield self.obj._connect()
                get.assert_called_once_with(self.obj.pid, self.obj)

    @testing.gen_test
    def test_connect_pooled_connection_invokes_add_handler(self):
        conn = yield self.obj._connect()
        self.obj._pool_manager.add(self.obj.pid, conn)
        with mock.patch.object(self.obj._pool_manager, 'get') as get:
            get.return_value = self.conn
            with mock.patch.object(self.io_loop, 'add_handler') as add_handler:
                yield self.obj._connect()
                add_handler.assert_called_once_with(self.conn.fileno(),
                                                    self.obj._on_io_events,
                                                    ioloop.IOLoop.WRITE)

    def test_psycopg2_connect_invokes_psycopg2_connect(self):
        with mock.patch('psycopg2.connect') as connect:
            self.obj._psycopg2_connect({})
            connect.assert_called_once_with(async=True)

    def test_on_io_events_returns_if_fd_not_present(self):
        with mock.patch.object(self.obj, '_poll_connection') as poll:
            self.obj._on_io_events(1337, ioloop.IOLoop.WRITE)
            poll.assert_not_called()

    def test_on_io_events_calls_poll_connection(self):
        with mock.patch.object(self.obj, '_poll_connection') as poll:
            self.obj._connections[1337] = True
            self.obj._on_io_events(1337, ioloop.IOLoop.WRITE)
            poll.assert_called_once_with(1337)

    def test_exec_cleanup_closes_cursor(self):
        with mock.patch.object(self.obj._pool_manager, 'free'):
            with mock.patch.object(self.obj._ioloop, 'remove_handler'):
                self.obj._connections[14] = mock.Mock()
                cursor = mock.Mock()
                cursor.close = mock.Mock()
                self.obj._exec_cleanup(cursor, 14)
                cursor.close.assert_called_once_with()

    def test_exec_cleanup_frees_connection(self):
        with mock.patch.object(self.obj._pool_manager, 'free') as pm_free:
            with mock.patch.object(self.obj._ioloop, 'remove_handler'):
                self.obj._connections[14] = conn = mock.Mock()
                self.obj._exec_cleanup(mock.Mock(), 14)
                pm_free.assert_called_once_with(self.obj.pid, conn)

    def test_exec_cleanup_frees_connection(self):
        with mock.patch.object(self.obj._pool_manager, 'free'):
            with mock.patch.object(self.obj._ioloop, 'remove_handler') as rh:
                self.obj._connections[14] = mock.Mock()
                self.obj._exec_cleanup(mock.Mock(), 14)
                rh.assert_called_once_with(14)

    def test_exec_removes_connection(self):
        with mock.patch.object(self.obj._pool_manager, 'free'):
            with mock.patch.object(self.obj._ioloop, 'remove_handler'):
                self.obj._connections[14] = mock.Mock()
                self.obj._exec_cleanup(mock.Mock(), 14)
                self.assertNotIn(14, self.obj._connections)

    def test_exec_removes_future(self):
        with mock.patch.object(self.obj._pool_manager, 'free'):
            with mock.patch.object(self.obj._ioloop, 'remove_handler'):
                self.obj._connections[14] = mock.Mock()
                self.obj._futures[14] = mock.Mock()
                self.obj._exec_cleanup(mock.Mock(), 14)
                self.assertNotIn(14, self.obj._futures)

    def test_pool_manager_add_failures_are_propagated(self):
        futures = []

        def add_future(future, callback):
            futures.append((future, callback))

        obj = tornado_session.TornadoSession()
        obj._ioloop = mock.Mock()
        obj._ioloop.add_future = add_future

        future = concurrent.Future()
        with mock.patch.object(obj._pool_manager, 'add') as add_method:
            add_method.side_effect = pool.PoolFullError(mock.Mock())
            obj._create_connection(future)
            self.assertEqual(len(futures), 1)

            connected_future, callback = futures.pop()
            connected_future.set_result(True)
            callback(connected_future)
            self.assertIs(future.exception(), add_method.side_effect)


class SessionPublicMethodTests(testing.AsyncTestCase):

    @testing.gen_test
    def test_callproc_invokes_execute(self):
        with mock.patch('queries.tornado_session.TornadoSession._execute') as \
                _execute:
            future = concurrent.Future()
            future.set_result(True)
            _execute.return_value = future
            obj = tornado_session.TornadoSession(io_loop=self.io_loop)
            yield obj.callproc('foo', ['bar'])
            _execute.assert_called_once_with('callproc', 'foo', ['bar'])

    @testing.gen_test
    def test_query_invokes_execute(self):
        with mock.patch('queries.tornado_session.TornadoSession._execute') as \
                _execute:
            future = concurrent.Future()
            future.set_result(True)
            _execute.return_value = future
            obj = tornado_session.TornadoSession(io_loop=self.io_loop)
            yield obj.query('SELECT 1')
            _execute.assert_called_once_with('execute', 'SELECT 1', None)

    @testing.gen_test
    def test_query_error_key_error(self):
        obj = tornado_session.TornadoSession(io_loop=self.io_loop)
        with self.assertRaises(KeyError):
            yield obj.query('SELECT * FROM foo WHERE bar=%(baz)s', {})

    @testing.gen_test
    def test_query_error_index_error(self):
        obj = tornado_session.TornadoSession(io_loop=self.io_loop)
        with self.assertRaises(IndexError):
            yield obj.query('SELECT * FROM foo WHERE bar=%s', [])
