"""
Tests for Manager class in the pool module

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import uuid

from queries import pool


class ManagerTests(unittest.TestCase):


    def setUp(self):
        self.manager = pool.PoolManager.instance()

    def test_singleton_behavior(self):
        self.assertEqual(pool.PoolManager.instance(), self.manager)

    def test_has_pool_false(self):
        self.assertNotIn(mock.Mock(), self.manager)

    def test_has_pool_true(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.assertIn(pid, self.manager)

    def test_adding_to_pool(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        psycopg2_conn = mock.Mock()
        self.manager.add(pid, psycopg2_conn)
        self.assertIn(psycopg2_conn, self.manager._pools[pid])

    def test_adding_to_pool_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        psycopg2_conn = mock.Mock()
        self.assertRaises(KeyError, self.manager.add, pid, psycopg2_conn)

    def test_clean_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.clean, pid)

    def test_clean_invokes_pool_clean(self):
        pid = str(uuid.uuid4())
        with mock.patch('queries.pool.Pool') as Pool:
            self.manager._pools[pid] = Pool()
            self.manager._pools[pid].clean = clean = mock.Mock()
            self.manager.clean(pid)
            clean.assert_called_once_with()

    def test_clean_removes_pool(self):
        pid = str(uuid.uuid4())
        with mock.patch('queries.pool.Pool') as Pool:
            self.manager._pools[pid] = Pool()
            self.manager.clean(pid)
            self.assertNotIn(pid, self.manager._pools)

    def test_create_prevents_duplicate_pool_id(self):
        pid = str(uuid.uuid4())
        with mock.patch('queries.pool.Pool') as Pool:
            self.manager._pools[pid] = Pool()
            self.assertRaises(KeyError, self.manager.create, pid, 10, 10, Pool)

    def test_create_created_default_pool_type(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.assertIsInstance(self.manager._pools[pid], pool.Pool)

    def test_create_created_passed_in_pool_type(self):
        pid = str(uuid.uuid4())

        class FooPool(pool.Pool):
            bar = True

        self.manager.create(pid, 10, 10, FooPool)
        self.assertIsInstance(self.manager._pools[pid], FooPool)

    def test_create_passes_in_idle_ttl(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid, 12)
        self.assertEqual(self.manager._pools[pid].idle_ttl, 12)

    def test_create_passes_in_max_size(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid, 10, 16)
        self.assertEqual(self.manager._pools[pid].max_size, 16)

    def test_get_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        session = mock.Mock()
        self.assertRaises(KeyError, self.manager.get, pid, session)

    def test_get_invokes_pool_get(self):
        pid = str(uuid.uuid4())
        session = mock.Mock()
        self.manager.create(pid)
        self.manager._pools[pid].get = get = mock.Mock()
        self.manager.get(pid, session)
        get.assert_called_once_with(session)

    def test_free_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        psycopg2_conn = mock.Mock()
        self.assertRaises(KeyError, self.manager.free, pid, psycopg2_conn)

    def test_free_invokes_pool_free(self):
        pid = str(uuid.uuid4())
        psycopg2_conn = mock.Mock()
        self.manager.create(pid)
        self.manager._pools[pid].free = free = mock.Mock()
        self.manager.free(pid, psycopg2_conn)
        free.assert_called_once_with(psycopg2_conn)

    def test_has_connection_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.has_connection, pid, None)

    def test_has_idle_connection_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.has_idle_connection, pid)

    def test_has_connection_returns_false(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.assertFalse(self.manager.has_connection(pid, mock.Mock()))

    def test_has_connection_returns_true(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        psycopg2_conn = mock.Mock()
        self.manager._pools[pid].connections[id(psycopg2_conn)] = psycopg2_conn
        self.assertTrue(self.manager.has_connection(pid, psycopg2_conn))

    def test_has_idle_connection_returns_false(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        with mock.patch('queries.pool.Pool.idle_connections',
                        new_callable=mock.PropertyMock) as idle_connections:
            idle_connections.return_value = 0
            self.assertFalse(self.manager.has_idle_connection(pid))

    def test_has_idle_connection_returns_true(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        with mock.patch('queries.pool.Pool.idle_connections',
                        new_callable=mock.PropertyMock) as idle_connections:
            idle_connections.return_value = 5
            self.assertTrue(self.manager.has_idle_connection(pid))

    def test_is_full_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.is_full, pid)

    def test_is_full_invokes_pool_is_full(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        with mock.patch('queries.pool.Pool.is_full',
                        new_callable=mock.PropertyMock) as is_full:
            self.manager.is_full(pid)
            is_full.assert_called_once_with()

    def test_lock_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.lock, pid, None, None)

    def test_lock_invokes_pool_lock(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.manager._pools[pid].lock = lock = mock.Mock()
        psycopg2_conn = mock.Mock()
        session = mock.Mock()
        self.manager.lock(pid, psycopg2_conn, session)
        lock.assert_called_once_with(psycopg2_conn, session)

    def test_remove_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.remove, pid)

    def test_remove_invokes_pool_close(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.manager._pools[pid].close = method = mock.Mock()
        self.manager.remove(pid)
        method.assert_called_once_with()

    def test_remove_deletes_pool(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.manager._pools[pid].close = mock.Mock()
        self.manager.remove(pid)
        self.assertNotIn(pid, self.manager._pools)

    def test_remove_connection_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.remove_connection, pid, None)

    def test_remove_connection_invokes_pool_remove(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.manager._pools[pid].remove = remove = mock.Mock()
        psycopg2_conn = mock.Mock()
        self.manager.remove_connection(pid, psycopg2_conn)
        remove.assert_called_once_with(psycopg2_conn)

    def test_size_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.size, pid)

    def test_size_returns_pool_length(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.assertEqual(self.manager.size(pid), len(self.manager._pools[pid]))

    def test_set_idle_ttl_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.set_idle_ttl, pid, None)

    def test_set_idle_ttl_invokes_pool_set_idle_ttl(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.manager._pools[pid].set_idle_ttl = set_idle_ttl = mock.Mock()
        self.manager.set_idle_ttl(pid, 256)
        set_idle_ttl.assert_called_once_with(256)

    def test_set_max_size_ensures_pool_exists(self):
        pid = str(uuid.uuid4())
        self.assertRaises(KeyError, self.manager.set_idle_ttl, pid, None)

    def test_set_max_size_invokes_pool_set_max_size(self):
        pid = str(uuid.uuid4())
        self.manager.create(pid)
        self.manager._pools[pid].set_max_size = set_max_size = mock.Mock()
        self.manager.set_max_size(pid, 128)
        set_max_size.assert_called_once_with(128)
