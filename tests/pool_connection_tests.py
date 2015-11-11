"""
Tests for Connection class in the pool module

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import weakref

from queries import pool


class ConnectionTests(unittest.TestCase):

    def setUp(self):
        self.handle = mock.Mock()
        self.handle.close = mock.Mock()
        self.handle.closed = True
        self.handle.isexecuting = mock.Mock(return_value=False)
        self.connection = pool.Connection(self.handle)
        self.connection.used_by = None

    def test_handle_should_match(self):
        self.assertEqual(self.handle, self.connection.handle)

    def test_busy_isexecuting_is_false(self):
        self.assertFalse(self.connection.busy)

    def test_busy_isexecuting_is_true(self):
        self.handle.isexecuting.return_value = True
        self.assertTrue(self.connection.busy)

    def test_busy_is_used(self):
        self.handle.isexecuting.return_value = False
        self.connection.used_by = mock.Mock()
        self.assertTrue(self.connection.busy)

    def test_executing_is_true(self):
        self.handle.isexecuting.return_value = True
        self.assertTrue(self.connection.executing)

    def test_executing_is_false(self):
        self.handle.isexecuting.return_value = False
        self.assertFalse(self.connection.executing)

    def test_locked_is_true(self):
        self.connection.used_by = mock.Mock()
        self.assertTrue(self.connection.locked)

    def test_locked_is_false(self):
        self.connection.used_by = None
        self.assertFalse(self.connection.locked)

    def test_closed_is_true(self):
        self.handle.closed = True
        self.assertTrue(self.connection.closed)

    def test_closed_is_false(self):
        self.handle.closed = False
        self.assertFalse(self.connection.closed)

    def test_close_raises_when_busy(self):
        self.handle.isexecuting.return_value = True
        self.assertRaises(pool.ConnectionBusyError, self.connection.close)

    def test_close_invokes_handle_close(self):
        self.handle.isexecuting.return_value = False
        self.connection.used_by = None
        self.connection.close()
        self.assertEqual(len(self.handle.close.mock_calls), 1)

    def test_free_raises_when_busy(self):
        self.handle.isexecuting.return_value = True
        self.assertRaises(pool.ConnectionBusyError, self.connection.free)

    def test_free_resets_used_by(self):
        self.handle.isexecuting.return_value = False
        self.connection.used_by = mock.Mock()
        self.connection.free()
        self.assertIsNone(self.connection.used_by)

    def test_id_value_matches(self):
        self.assertEqual(id(self.handle), self.connection.id)

    def test_lock_raises_when_busy(self):
        self.connection.used_by = mock.Mock()
        self.assertRaises(pool.ConnectionBusyError,
                          self.connection.lock, mock.Mock())

    def test_lock_session_used_by(self):
        session = mock.Mock()
        self.connection.lock(session)
        self.assertIn(self.connection.used_by,
                      weakref.getweakrefs(session))
