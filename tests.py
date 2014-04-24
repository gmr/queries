"""
Tests for the pgsql_wrapper module

"""
import mock
import time

try:
    import unittest2
except ImportError:
    import unittest

import pgsql_wrapper


class ConnectionCachingTests(unittest.TestCase):

    def setUp(self):
        pgsql_wrapper._add_cached_connection('cc0', self.__class__)

    def tearDown(self):
        for key in ['cc0', 'cc1', 'cc2', 'cc3', 'cc4']:
            if key in pgsql_wrapper.CONNECTIONS:
                del pgsql_wrapper.CONNECTIONS[key]

    def test_generate_hash(self):
        """DSN hash generation yields expected value"""
        value = 'host=localhost;port=5432;user=postgres;dbname=postgres'
        expectation = 'e73e565b90b37655fdccad5006339f608a1f7482'
        self.assertEqual(pgsql_wrapper._generate_connection_hash(value),
                         expectation)

    def test_add_cached_connection_adds_value(self):
        """Cconnection should already exist in the connection cache"""
        self.assertIn('cc0', pgsql_wrapper.CONNECTIONS)

    def test_get_cached_connection_returns_proper_value(self):
        """Fetching cached connection returns proper value"""
        self.assertEqual(pgsql_wrapper._get_cached_connection('cc0'),
                         self.__class__)

    def test_get_cached_connection_increments_counter(self):
        """Fetching cached connection increments client counter"""
        value = pgsql_wrapper.CONNECTIONS.get('cc0', {}).get('clients', 0)
        pgsql_wrapper._get_cached_connection('cc0')
        self.assertEqual(pgsql_wrapper.CONNECTIONS['cc0']['clients'],
                         value + 1)

    def test_add_cached_connection_new(self):
        """Adding a new connection to module cache returns True"""
        self.assertTrue(pgsql_wrapper._add_cached_connection('cc1', True))

    def test_add_cached_connection_existing(self):
        """Adding an existing connection to module cache returns False"""
        pgsql_wrapper._add_cached_connection('cc2', True)
        self.assertFalse(pgsql_wrapper._add_cached_connection('cc2', True))

    def test_new_then_freed_cached_connection_has_no_clients(self):
        """Freeing connection with one client should decrement counter"""
        pgsql_wrapper._add_cached_connection('cc3', True)
        pgsql_wrapper._free_cached_connection('cc3')
        self.assertEqual(pgsql_wrapper.CONNECTIONS['cc3']['clients'], 0)

    def test_free_cached_connection(self):
        """Freeing connection should update last timestamp"""
        pgsql_wrapper._add_cached_connection('cc4', True)
        pgsql_wrapper._free_cached_connection('cc4')
        self.assertAlmostEqual(pgsql_wrapper.CONNECTIONS['cc4']['last_client'],
                               int(time.time()))


class ConnectionCacheExpirationTests(unittest.TestCase):

    def setUp(self):
        pgsql_wrapper._add_cached_connection('cce_test', self.__class__)

    def test_cache_expiration(self):
        """Check that unused connection expires"""
        return_value = time.time() - pgsql_wrapper.CACHE_TTL - 1
        with mock.patch('time.time') as ptime:
            ptime.return_value = return_value
            pgsql_wrapper._free_cached_connection('cce_test')
        pgsql_wrapper._check_for_unused_expired_connections()
        self.assertNotIn('cce_test', pgsql_wrapper.CONNECTIONS)
