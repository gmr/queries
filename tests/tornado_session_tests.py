"""
Tests for functionality in the tornado_session module

"""
import mock
import tempfile
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from psycopg2 import extras
import psycopg2

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

    def test_creates_empty_listeners_dict(self):
        self.assertDictEqual(self.obj._listeners, {})

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


class SessionTests(testing.AsyncTestCase):

    @mock.patch('psycopg2.connect')
    @mock.patch('psycopg2.extensions.register_type')
    @mock.patch('psycopg2.extras.register_uuid')
    @mock.patch('queries.utils.uri_to_kwargs')
    def setUp(self, uri_to_kwargs, register_uuid, register_type, connect):

        super(SessionTests, self).setUp()

        self.conn = mock.Mock()
        self.conn.autocommit = False
        self.conn.closed = False
        self.conn.cursor = mock.Mock()

        self.conn.fileno = mock.Mock(return_value=True)
        self.conn.isexecuting = mock.Mock(return_value=False)
        self.conn.reset = mock.Mock()
        self.conn.status = psycopg2.extensions.STATUS_BEGIN

        self.psycopg2_connect = connect
        self.psycopg2_register_type = register_type
        self.psycopg2_register_uuid = register_uuid

        self.uri_to_kwargs = uri_to_kwargs
        self.uri_to_kwargs.return_value = {'host': 'localhost',
                                           'port': 5432,
                                           'user': 'foo',
                                           'password': 'bar',
                                           'dbname': 'foo'}

    @testing.gen_test
    def test_callproc_invokes_execute(self):
        with mock.patch('queries.tornado_session.TornadoSession._execute') as \
                _execute:
            future = concurrent.Future()
            future.set_result(True)
            _execute.return_value = future
            obj = tornado_session.TornadoSession(io_loop=self.io_loop)
            result = yield obj.callproc('foo', ['bar'])
            _execute.assert_called_once_with('callproc', 'foo', ['bar'])

    @testing.gen_test
    def test_query_invokes_execute(self):
        with mock.patch('queries.tornado_session.TornadoSession._execute') as \
                _execute:
            future = concurrent.Future()
            future.set_result(True)
            _execute.return_value = future
            obj = tornado_session.TornadoSession(io_loop=self.io_loop)
            result = yield obj.query('SELECT 1')
            _execute.assert_called_once_with('execute', 'SELECT 1', None)




