"""
Connection Pool Tests

"""
import mock
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from queries import pool
from queries.pool import CLIENTS, LAST, TTL


class ConnectionPoolTests(unittest.TestCase):

    def setUp(self):
        pool.add_connection('cc0', self.__class__)

    def tearDown(self):
        for key in ['cc0', 'cc1', 'cc2', 'cc3', 'cc4']:
            if key in pool.CONNECTIONS:
                del pool.CONNECTIONS[key]

    def test_add_connection_adds_value(self):
        """Connection should already exist in the connection pool"""
        self.assertIn('cc0', pool.CONNECTIONS)

    def test_get_connection_returns_proper_value(self):
        """Fetching connection from pool returns proper value"""
        self.assertEqual(pool.get_connection('cc0'), self.__class__)

    def test_get_connection_increments_counter(self):
        """Fetching connection from pool increments client counter"""
        value = pool.CONNECTIONS.get('cc0', {}).get(CLIENTS, 0)
        pool.get_connection('cc0')
        self.assertEqual(pool.CONNECTIONS['cc0'][CLIENTS], value + 1)

    def test_add_connection_new(self):
        """Adding a new connection to the pool returns True"""
        self.assertTrue(pool.add_connection('cc1', True))

    def test_add_connection_existing(self):
        """Adding an existing connection to the pool returns False"""
        pool.add_connection('cc2', True)
        self.assertFalse(pool.add_connection('cc2', True))

    def test_new_then_freed_connection_has_no_clients(self):
        """Freeing connection with one client should decrement counter"""
        pool.add_connection('cc3', True)
        pool.free_connection('cc3')
        self.assertEqual(pool.CONNECTIONS['cc3'][CLIENTS], 0)

    def test_free_connection(self):
        """Freeing connection should update last timestamp"""
        pool.add_connection('cc4', True)
        pool.free_connection('cc4')
        self.assertAlmostEqual(pool.CONNECTIONS['cc4'][LAST], int(time.time()))

    def test_remove_connection(self):
        """Freeing connection should update last timestamp"""
        pool.add_connection('cc5', True)
        pool.remove_connection('cc5')
        self.assertNotIn('cc5', pool.CONNECTIONS)


class ConnectionPoolExpirationTests(unittest.TestCase):

    def setUp(self):
        pool.add_connection('cce_test', self.__class__)

    def test_pool_expiration(self):
        """Check that unused connection expires"""
        return_value = time.time() - TTL - 1
        with mock.patch('time.time') as ptime:
            ptime.return_value = return_value
            pool.free_connection('cce_test')
        pool.check_for_unused_expired_connections()
        self.assertNotIn('cce_test', pool.CONNECTIONS)