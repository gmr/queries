"""
Connection Pool Tests

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


class AddConnectionTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_pool_id_is_in_pools(self):
        """Ensure the pool.Pools dict has an entry for pid"""
        self.assertIn(self.pid, pool.Pools)

    def test_session_ref_is_in_pool(self):
        """Ensure that the session weakref is in the pool"""
        self.assertIn(weakref.ref(self), pool.Pools[self.pid].sessions)

    def test_connection_is_in_pool(self):
        """Ensure that the session weakref is in the pool"""
        self.assertIn(self.connection, pool.Pools[self.pid].connections)

    def test_last_used_is_zero_for_pool(self):
        """Ensure that the last_used value is 0 for pool"""
        self.assertEqual(pool.Pools[self.pid].last_use, 0)

    def test_max_connection_reached_raises_exception(self):
        """Ensure that a ValueError is raised with too many connections"""
        for iteration in range(0, pool.MAX_CONNECTIONS):
            conn = 'conn%i' % iteration
            pool.add_connection(self.pid, self, conn)
        self.assertRaises(ValueError, pool.add_connection,
                          self.pid, self, 'ERROR')

    def test_count_of_session_references(self):
        """Ensure a single session is only added once to the pool sessions"""
        for iteration in range(0, pool.MAX_CONNECTIONS):
            conn = 'conn%i' % iteration
            pool.add_connection(self.pid, self, conn)
        self.assertEqual(len(pool.Pools[self.pid].sessions), 1)


class CleanPoolTests(unittest.TestCase):

    def setUp(self):
        self.cclose = mock.Mock()
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.connection.close = self.cclose
        self.pid = str(uuid.uuid4())
        self.session = mock.Mock('queries.session.Session')
        pool.add_connection(self.pid, self.session, self.connection)

    def test_idle_pool_removed(self):
        """Ensure an idle pool is removed"""
        pool.Pools[self.pid] = \
            pool.Pools[self.pid]._replace(sessions=set(),
                                          last_use=int(time.time()-pool.TTL-2))
        pool.clean_pools()
        self.assertNotIn(self.pid, pool.Pools)

    def test_idle_connections_closed(self):
        """Ensure a connection in an idle pool is closed"""
        pool.Pools[self.pid] = \
            pool.Pools[self.pid]._replace(sessions=set(),
                                          last_use=int(time.time()-pool.TTL-2))
        pool.clean_pools()
        self.cclose.assert_called_once_with()


class ConnectionInPoolTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_has_pool_returns_true(self):
        """Ensure that connection_in_pool returns True"""
        self.assertTrue(pool.connection_in_pool(self.pid, self.connection))

    def test_has_pool_returns_false(self):
        """Ensure that connection_in_pool returns False"""
        self.assertFalse(pool.connection_in_pool(self.pid, self))


class GetConnectionTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.connection.isexecuting = mock.Mock()
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_when_is_executing(self):
        """When connection is executing get_connection return None"""
        self.connection.isexecuting.return_value = True
        self.assertIsNone(pool.get_connection(self.pid))

    def test_when_is_idle(self):
        """When connection is executing get_connection returns connection"""
        self.connection.isexecuting.return_value = False
        self.assertEqual(pool.get_connection(self.pid), self.connection)


class HasIdleConnectionTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.connection.isexecuting = mock.Mock()
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_when_is_executing(self):
        """When connection is executing has_idle_connection return False"""
        self.connection.isexecuting.return_value = True
        self.assertFalse(pool.has_idle_connection(self.pid))

    def test_when_is_idle(self):
        """When connection is executing has_idle_connection return False"""
        self.connection.isexecuting.return_value = False
        self.assertTrue(pool.has_idle_connection(self.pid))


class HasPoolTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_has_pool_returns_true(self):
        """Ensure that has_pool returns True when pool exists"""
        self.assertTrue(pool.has_pool(self.pid))

    def test_has_pool_returns_false(self):
        """Ensure that has_pool returns False when pool doesnt exist"""
        self.assertFalse(pool.has_pool(self))


class RemoveConnectionTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_remove_connection_removes_connection(self):
        """Ensure a removed connection is not in pool"""
        pool.remove_connection(self.pid, self.connection)
        self.assertNotIn(self.connection, pool.Pools[self.pid].connections)

    def test_empty_pool_removed(self):
        """Ensure a removed connection is not in pool"""
        pool.remove_connection(self.pid, self.connection)
        pool.clean_pools()
        self.assertNotIn(self.pid, pool.Pools)

    def test_invalid_connection_fails_silently(self):
        """Ensure that passing an invalid pid doesnt raise an exception"""
        pool.remove_connection(self.pid, self)

    def test_invalid_pid_fails_silently(self):
        """Ensure passing an invalid pid doesnt not raise exception"""
        pool.remove_connection(self.connection, self)


class RemoveSessionTests(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock('queries.session.Session')
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.connection.close = mock.Mock()
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self.session, self.connection)

    def test_remove_sets_last_use(self):
        """Ensure that last_use is set for a pool when last session removed"""
        pool.remove_session(self.pid, self.session)
        self.assertEqual(pool.Pools[self.pid].last_use, int(time.time()))

    def test_remove_session_removes_session(self):
        """Ensure a removed session's weakref is not in pool"""
        pool.remove_session(self.pid, self.session)
        self.assertNotIn(weakref.ref(self), pool.Pools[self.pid].sessions)

    def test_dead_weakref_removed(self):
        """Ensure a deleted session obj is not in the pool"""
        del self.session
        pool.clean_pools()
        self.assertEqual(len(pool.Pools[self.pid].sessions), 0)

    def test_dead_weakref_removed_but_pool_not_removed(self):
        """Ensure a pool with no remaining sessions is not removed"""
        del self.session
        pool.clean_pools()
        self.assertIn(self.pid, pool.Pools)

    def test_invalid_session_fails_silently(self):
        """Ensure that passing an invalid pid doesnt raise an exception"""
        pool.remove_session(self.pid, self.connection)

    def test_invalid_pid_fails_silently(self):
        """Ensure passing an invalid pid doesnt not raise exception"""
        pool.remove_session(self.connection, self.session)


class SessionInPoolTests(unittest.TestCase):

    def setUp(self):
        self.connection = mock.Mock('psycopg2._psycopg.connection')
        self.pid = str(uuid.uuid4())
        pool.add_connection(self.pid, self, self.connection)

    def test_has_pool_returns_true(self):
        """Ensure that session_in_pool returns True when session exists"""
        self.assertTrue(pool.session_in_pool(self.pid, self))

    def test_has_pool_returns_false(self):
        """Ensure that session_in_pool returns False when it doesnt exist"""
        self.assertFalse(pool.session_in_pool(self.pid, self.connection))
