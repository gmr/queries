"""
Tests for functionality in the tornado_session module

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from psycopg2 import extras
from tornado import gen
from tornado import ioloop

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
        self.assertDictEqual(self.obj._callbacks, {})

    def test_creates_empty_connections_dict(self):
        self.assertDictEqual(self.obj._connections, {})

    def test_creates_empty_exceptions_dict(self):
        self.assertDictEqual(self.obj._exceptions, {})

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
