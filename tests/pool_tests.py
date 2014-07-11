"""
Tests for functionality in the pool module

"""
import mock
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import uuid
import weakref

from queries import pool


class PoolTests(unittest.TestCase):

    def test_id_is_set(self):
        pool_id = str(uuid.uuid4())
        obj = pool.Pool(pool_id)
        self.assertEqual(obj._id, pool_id)

    def test_id_property(self):
        pool_id = str(uuid.uuid4())
        obj = pool.Pool(pool_id)
        self.assertEqual(obj.id, pool_id)

    def test_idle_ttl_is_default(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertEqual(obj.idle_ttl, pool.DEFAULT_IDLE_TTL)

    def test_max_size_is_default(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertEqual(obj.max_size, pool.DEFAULT_MAX_SIZE)

    def test_idle_ttl_constructor_assignment(self):
        obj = pool.Pool(str(uuid.uuid4()), 10)
        self.assertEqual(obj.idle_ttl, 10)

    def test_max_size_constructor_assignment(self):
        obj = pool.Pool(str(uuid.uuid4()), max_size=10)
        self.assertEqual(obj.max_size, 10)

    def test_idle_ttl_assignment(self):
        obj = pool.Pool(str(uuid.uuid4()))
        obj.set_idle_ttl(10)
        self.assertEqual(obj.idle_ttl, 10)

    def test_max_size_assignment(self):
        obj = pool.Pool(str(uuid.uuid4()))
        obj.set_max_size(10)
        self.assertEqual(obj.max_size, 10)

    def test_pool_doesnt_contain_connection(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertNotIn('foo', obj)

    def test_default_connection_count(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertEqual(len(obj), 0)

    def test_add_new_connection(self):
        psycopg2_conn = mock.Mock()
        obj = pool.Pool(str(uuid.uuid4()))
        obj.add(psycopg2_conn)
        self.assertIn(psycopg2_conn, obj)

    def test_connection_count_after_add(self):
        psycopg2_conn = mock.Mock()
        obj = pool.Pool(str(uuid.uuid4()))
        obj.add(psycopg2_conn)
        self.assertEqual(len(obj), 1)

    def test_add_existing_connection_raises_on_second_add(self):
        psycopg2_conn = mock.Mock()
        obj = pool.Pool(str(uuid.uuid4()))
        obj.add(psycopg2_conn)
        self.assertRaises(ValueError, obj.add, psycopg2_conn)

    def test_add_when_pool_is_full_raises(self):
        obj = pool.Pool(str(uuid.uuid4()), max_size=1)
        obj.add(mock.Mock())
        mock_conn = mock.Mock()
        self.assertRaises(pool.PoolFullError, obj.add, mock_conn)

    def test_closed_conn_invokes_remove_on_clean(self):
        psycopg2_conn = mock.Mock()
        psycopg2_conn.closed = True
        obj = pool.Pool(str(uuid.uuid4()))
        obj.remove = mock.Mock()
        obj.add(psycopg2_conn)
        obj.clean()
        obj.remove.assert_called_once_with(psycopg2_conn)

    def test_clean_closes_all_when_idle(self):
        obj = pool.Pool(str(uuid.uuid4()), idle_ttl=10)
        obj.idle_start = time.time() - 20
        obj.close = mock.Mock()
        obj.clean()
        obj.close.assert_called_once_with()

    def test_close_close_removes_all(self):

        obj = pool.Pool(str(uuid.uuid4()))
        obj.remove = mock.Mock()
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        obj.close()
        obj.remove.assert_hass_calls(psycopg2_conns)

    def test_free_invokes_connection_free(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conn = mock.Mock()
        obj.add(psycopg2_conn)
        conn = obj._connection(psycopg2_conn)
        conn.free = mock.Mock()
        obj.free(psycopg2_conn)
        conn.free.assert_called_once_with()

    def test_free_raises_not_found_exception(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conn = mock.Mock()
        obj.add(psycopg2_conn)
        conn = obj._connection(psycopg2_conn)
        conn.free = mock.Mock()
        obj.free(psycopg2_conn)
        conn.free.assert_called_once_with()

    def test_free_resets_idle_start(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False):
            [obj.add(conn) for conn in psycopg2_conns]
            for psycopg2_conn in psycopg2_conns:
                conn = obj._connection(psycopg2_conn)
                conn.free = mock.Mock()
            obj.free(psycopg2_conns[1])
            self.assertAlmostEqual(int(obj.idle_start), int(time.time()))

    def test_free_raises_on_not_found(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertRaises(pool.ConnectionNotFoundError, obj.free, mock.Mock())

    def test_get_returns_first_psycopg2_conn(self):
        obj = pool.Pool(str(uuid.uuid4()))
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False):
            psycopg2_conns = [mock.Mock(), mock.Mock()]
            [obj.add(conn) for conn in psycopg2_conns]
            session = mock.Mock()
            self.assertEqual(obj.get(session), psycopg2_conns[0])

    def test_get_locks_first_psycopg2_conn(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        lock = mock.Mock()
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False, lock=lock):
            session = mock.Mock()
            obj.get(session)
            lock.assert_called_once_with(session)

    def test_get_resets_idle_start_to_none(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False):
            session = mock.Mock()
            obj.get(session)
            self.assertIsNone(obj.idle_start)

    def test_get_raises_when_no_idle_connections(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        session = mock.Mock()
        self.assertRaises(pool.NoIdleConnectionsError, obj.get, session)

    def test_idle_connections(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False):
            self.assertListEqual([c.handle for c in obj.idle_connections],
                                 psycopg2_conns)

    def test_idle_duration_when_none(self):
        obj = pool.Pool(str(uuid.uuid4()))
        obj.idle_start = None
        self.assertEqual(obj.idle_duration, 0)

    def test_idle_duration_when_set(self):
        obj = pool.Pool(str(uuid.uuid4()))
        obj.idle_start = time.time() - 5
        self.assertAlmostEqual(int(obj.idle_duration), 5)

    def test_is_full_property_when_full(self):
        obj = pool.Pool(str(uuid.uuid4()), max_size=2)
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        self.assertTrue(obj.is_full)

    def test_is_full_property_when_not_full(self):
        obj = pool.Pool(str(uuid.uuid4()), max_size=3)
        psycopg2_conns = [mock.Mock(), mock.Mock()]
        [obj.add(conn) for conn in psycopg2_conns]
        self.assertFalse(obj.is_full)

    def test_connection_lock_is_called_when_lock_is(self):
        with mock.patch('queries.pool.Connection.lock') as lock:
            obj = pool.Pool(str(uuid.uuid4()))
            psycopg2_conn = mock.Mock()
            obj.add(psycopg2_conn)
            session = mock.Mock()
            obj.lock(psycopg2_conn, session)
            lock.assert_called_once_with(session)

    def test_locks_raises_when_connection_not_found(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertRaises(pool.ConnectionNotFoundError, obj.lock,
                          mock.Mock(), mock.Mock())

    def test_lock_resets_idle_start(self):
        with mock.patch('queries.pool.Connection.lock'):
            obj = pool.Pool(str(uuid.uuid4()))
            obj.idle_start = time.time()
            psycopg2_conn = mock.Mock()
            obj.add(psycopg2_conn)
            obj.lock(psycopg2_conn, mock.Mock())
            self.assertIsNone(obj.idle_start)

    def test_remove_removes_connection(self):
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False):
            obj = pool.Pool(str(uuid.uuid4()))
            psycopg2_conn = mock.Mock()
            obj.add(psycopg2_conn)
            obj.remove(psycopg2_conn)
            self.assertNotIn(psycopg2_conn, obj)

    def test_remove_closes_connection(self):
        close_method = mock.Mock()
        with mock.patch.multiple('queries.pool.Connection',
                                 busy=False, closed=False,
                                 close=close_method):
            obj = pool.Pool(str(uuid.uuid4()))
            psycopg2_conn = mock.Mock()
            obj.add(psycopg2_conn)
            obj.remove(psycopg2_conn)
            close_method.assert_called_once_with()

    def test_remove_raises_when_connection_not_found(self):
        obj = pool.Pool(str(uuid.uuid4()))
        self.assertRaises(pool.ConnectionNotFoundError, obj.remove,
                          mock.Mock())

    def test_remove_raises_when_connection_is_busy(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conn = mock.Mock()
        obj.add(psycopg2_conn)
        self.assertRaises(pool.ConnectionBusyError, obj.remove,
                          psycopg2_conn)

    def test__connection_returns_handle(self):
        obj = pool.Pool(str(uuid.uuid4()))
        psycopg2_conn = mock.Mock()
        obj.add(psycopg2_conn)
        self.assertEqual(obj._connection(psycopg2_conn).handle, psycopg2_conn)
