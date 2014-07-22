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
        psycopg2_conn = mock.Mock()
        self.assertRaises(KeyError, self.manager.clean, pid)
