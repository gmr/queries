"""
Connection Pooling

"""
import logging
import os
import threading
import time
import weakref

import psycopg2

LOGGER = logging.getLogger(__name__)

DEFAULT_IDLE_TTL = 60
DEFAULT_MAX_SIZE = int(os.environ.get('QUERIES_MAX_POOL_SIZE', 1))


class Connection(object):
    """Contains the handle to the connection, the current state of the
    connection and methods for manipulating the state of the connection.

    """
    _lock = threading.Lock()

    def __init__(self, handle):
        self.handle = handle
        self.used_by = None

    def close(self):
        """Close the connection

        :raises: ConnectionBusyError

        """
        LOGGER.debug('Connection %s closing', self.id)
        if self.busy:
            raise ConnectionBusyError(self)
        with self._lock:
            if not self.handle.closed:
                try:
                    self.handle.close()
                except psycopg2.InterfaceError as error:
                    LOGGER.error('Error closing socket: %s', error)

    @property
    def closed(self):
        """Return if the psycopg2 connection is closed.

        :rtype: bool

        """
        return self.handle.closed

    @property
    def busy(self):
        """Return if the connection is currently executing a query or is locked
        by a session that still exists.

        :rtype: bool

        """
        if self.handle.isexecuting():
            return True
        elif self.used_by is None:
            return False
        return not self.used_by() is None

    @property
    def executing(self):
        """Return if the connection is currently executing a query

        :rtype: bool

        """
        return self.handle.isexecuting()

    def free(self):
        """Remove the lock on the connection if the connection is not active

        :raises: ConnectionBusyError

        """
        LOGGER.debug('Connection %s freeing', self.id)
        if self.handle.isexecuting():
            raise ConnectionBusyError(self)
        with self._lock:
            self.used_by = None
        LOGGER.debug('Connection %s freed', self.id)

    @property
    def id(self):
        """Return id of the psycopg2 connection object

        :rtype: int

        """
        return id(self.handle)

    def lock(self, session):
        """Lock the connection, ensuring that it is not busy and storing
        a weakref for the session.

        :param queries.Session session: The session to lock the connection with
        :raises: ConnectionBusyError

        """
        if self.busy:
            raise ConnectionBusyError(self)
        with self._lock:
            self.used_by = weakref.ref(session)
        LOGGER.debug('Connection %s locked', self.id)

    @property
    def locked(self):
        """Return if the connection is currently exclusively locked

        :rtype: bool

        """
        return self.used_by is not None


class Pool(object):
    """A connection pool for gaining access to and managing connections"""
    _lock = threading.Lock()

    idle_start = None
    idle_ttl = DEFAULT_IDLE_TTL
    max_size = DEFAULT_MAX_SIZE

    def __init__(self,
                 pool_id,
                 idle_ttl=DEFAULT_IDLE_TTL,
                 max_size=DEFAULT_MAX_SIZE):
        self.connections = {}
        self._id = pool_id
        self.idle_ttl = idle_ttl
        self.max_size = max_size

    def __contains__(self, connection):
        """Return True if the pool contains the connection"""
        return id(connection) in self.connections

    def __len__(self):
        """Return the number of connections in the pool"""
        return len(self.connections)

    def add(self, connection):
        """Add a new connection to the pool

        :param connection: The connection to add to the pool
        :type connection: psycopg2.extensions.connection
        :raises: PoolFullError

        """
        if id(connection) in self.connections:
            raise ValueError('Connection already exists in pool')

        if len(self.connections) == self.max_size:
            LOGGER.warning('Race condition found when adding new connection')
            try:
                connection.close()
            except (psycopg2.Error, psycopg2.Warning) as error:
                LOGGER.error('Error closing the conn that cant be used: %s',
                             error)
            raise PoolFullError(self)
        with self._lock:
            self.connections[id(connection)] = Connection(connection)
        LOGGER.debug('Pool %s added connection %s', self.id, id(connection))

    def clean(self):
        """Clean the pool by removing any closed connections and if the pool's
        idle has exceeded its idle TTL, remove all connections.

        """
        LOGGER.debug('Cleaning the pool')
        for connection in [self.connections[k] for k in self.connections if
                           self.connections[k].closed]:
            LOGGER.debug('Removing %s', connection.id)
            self.remove(connection.handle)

        if self.idle_duration > self.idle_ttl:
            self.close()

        LOGGER.debug('Pool %s cleaned', self.id)

    def close(self):
        """Close the pool by closing and removing all of the connections"""
        for cid in list(self.connections.keys()):
            self.remove(self.connections[cid].handle)
        LOGGER.debug('Pool %s closed', self.id)

    def free(self, connection):
        """Free the connection from use by the session that was using it.

        :param connection: The connection to free
        :type connection: psycopg2.extensions.connection
        :raises: ConnectionNotFoundError

        """
        LOGGER.debug('Pool %s freeing connection %s', self.id, id(connection))
        try:
            self._connection(connection).free()
        except KeyError:
            raise ConnectionNotFoundError(self.id, id(connection))

        if self.idle_connections == list(self.connections.values()):
            with self._lock:
                self.idle_start = time.time()
        LOGGER.debug('Pool %s freed connection %s', self.id, id(connection))

    def get(self, session):
        """Return an idle connection and assign the session to the connection

        :param queries.Session session: The session to assign
        :rtype: psycopg2.extensions.connection
        :raises: NoIdleConnectionsError

        """
        idle = self.idle_connections
        if idle:
            connection = idle.pop(0)
            connection.lock(session)
            if self.idle_start:
                with self._lock:
                    self.idle_start = None
            return connection.handle
        raise NoIdleConnectionsError(self.id)

    @property
    def id(self):
        """Return the ID for this pool

        :rtype: str

        """
        return self._id

    @property
    def idle_connections(self):
        """Return a list of idle connections

        :rtype: list

        """
        return [self.connections[k] for k in self.connections if
                not self.connections[k].busy and
                not self.connections[k].closed]

    @property
    def idle_duration(self):
        """Return the number of seconds that the pool has had no active
        connections.

        :rtype: float

        """
        if self.idle_start is None:
            return 0
        return time.time() - self.idle_start

    @property
    def is_full(self):
        """Return True if there are no more open slots for connections.

        :rtype: bool

        """
        return len(self.connections) >= self.max_size

    def lock(self, connection, session):
        """Explicitly lock the specified connection

        :type connection: psycopg2.extensions.connection
        :param connection: The connection to lock
        :param queries.Session session: The session to hold the lock

        """
        cid = id(connection)
        try:
            self._connection(connection).lock(session)
        except KeyError:
            raise ConnectionNotFoundError(self.id, cid)
        else:
            if self.idle_start:
                with self._lock:
                    self.idle_start = None
        LOGGER.debug('Pool %s locked connection %s', self.id, cid)

    def remove(self, connection):
        """Remove the connection from the pool

        :param connection: The connection to remove
        :type connection: psycopg2.extensions.connection
        :raises: ConnectionNotFoundError
        :raises: ConnectionBusyError

        """
        cid = id(connection)
        if cid not in self.connections:
            raise ConnectionNotFoundError(self.id, cid)
        self._connection(connection).close()
        with self._lock:
            del self.connections[cid]
        LOGGER.debug('Pool %s removed connection %s', self.id, cid)

    def shutdown(self):
        """Forcefully shutdown the entire pool, closing all non-executing
        connections.

        :raises: ConnectionBusyError

        """
        with self._lock:
            for cid in list(self.connections.keys()):
                if self.connections[cid].executing:
                    raise ConnectionBusyError(cid)
                if self.connections[cid].locked:
                    self.connections[cid].free()
                self.connections[cid].close()
                del self.connections[cid]

    def set_idle_ttl(self, ttl):
        """Set the idle ttl

        :param int ttl: The TTL when idle

        """
        with self._lock:
            self.idle_ttl = ttl

    def set_max_size(self, size):
        """Set the maximum number of connections

        :param int size: The maximum number of connections

        """
        with self._lock:
            self.max_size = size

    def _connection(self, connection):
        """Return a connection object for the given psycopg2 connection

        :param connection: The connection to return a parent for
        :type connection: psycopg2.extensions.connection
        :rtype: Connection

        """
        return self.connections[id(connection)]


class PoolManager(object):
    """The connection pool object implements behavior around connections and
    their use in queries.Session objects.

    We carry a pool id instead of the connection URI so that we will not be
    carrying the URI in memory, creating a possible security issue.

    """
    _lock = threading.Lock()
    _pools = {}

    def __contains__(self, pid):
        """Returns True if the pool exists

        :param str pid: The pool id to check for
        :rtype: bool

        """
        return pid in self.__class__._pools

    @classmethod
    def instance(cls):
        """Only allow a single PoolManager instance to exist, returning the
        handle for it.

        :rtype: PoolManager

        """
        if not hasattr(cls, '_instance'):
            with cls._lock:
                cls._instance = cls()
        return cls._instance

    @classmethod
    def add(cls, pid, connection):
        """Add a new connection and session to a pool.

        :param str pid: The pool id
        :type connection: psycopg2.extensions.connection
        :param connection: The connection to add to the pool

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            cls._pools[pid].add(connection)

    @classmethod
    def clean(cls, pid):
        """Clean the specified pool, removing any closed connections or
        stale locks.

        :param str pid: The pool id to clean

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            cls._pools[pid].clean()

            # If the pool has no open connections, remove it
            if not len(cls._pools[pid]):
                del cls._pools[pid]

    @classmethod
    def create(cls, pid, idle_ttl=DEFAULT_IDLE_TTL, max_size=DEFAULT_MAX_SIZE):
        """Create a new pool, with the ability to pass in values to override
        the default idle TTL and the default maximum size.

        A pool's idle TTL defines the amount of time that a pool can be open
        without any sessions before it is removed.

        A pool's max size defines the maximum number of connections that can
        be added to the pool to prevent unbounded open connections.

        :param str pid: The pool ID
        :param int idle_ttl: Time in seconds for the idle TTL
        :param int max_size: The maximum pool size
        :raises: KeyError

        """
        if pid in cls._pools:
            raise KeyError('Pool %s already exists' % pid)
        with cls._lock:
            LOGGER.debug("Creating Pool: %s (%i/%i)", pid, idle_ttl, max_size)
            cls._pools[pid] = Pool(pid, idle_ttl, max_size)

    @classmethod
    def get(cls, pid, session):
        """Get an idle, unused connection from the pool. Once a connection has
        been retrieved, it will be marked as in-use until it is freed.

        :param str pid: The pool ID
        :param queries.Session session: The session to assign to the connection
        :rtype: psycopg2.extensions.connection

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            return cls._pools[pid].get(session)

    @classmethod
    def free(cls, pid, connection):
        """Free a connection that was locked by a session

        :param str pid: The pool ID
        :param connection: The connection to remove
        :type connection: psycopg2.extensions.connection

        """
        with cls._lock:
            LOGGER.debug('Freeing %s from pool %s', id(connection), pid)
            cls._ensure_pool_exists(pid)
            cls._pools[pid].free(connection)

    @classmethod
    def has_connection(cls, pid, connection):
        """Check to see if a pool has the specified connection

        :param str pid: The pool ID
        :param connection: The connection to check for
        :type connection: psycopg2.extensions.connection
        :rtype: bool

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            return connection in cls._pools[pid]

    @classmethod
    def has_idle_connection(cls, pid):
        """Check to see if a pool has an idle connection

        :param str pid: The pool ID
        :rtype: bool

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            return bool(cls._pools[pid].idle_connections)

    @classmethod
    def is_full(cls, pid):
        """Return a bool indicating if the specified pool is full

        :param str pid: The pool id
        :rtype: bool

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            return cls._pools[pid].is_full

    @classmethod
    def lock(cls, pid, connection, session):
        """Explicitly lock the specified connection in the pool

        :param str pid: The pool id
        :type connection: psycopg2.extensions.connection
        :param connection: The connection to add to the pool
        :param queries.Session session: The session to hold the lock

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            cls._pools[pid].lock(connection, session)

    @classmethod
    def remove(cls, pid):
        """Remove a pool, closing all connections

        :param str pid: The pool ID

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            cls._pools[pid].close()
            del cls._pools[pid]

    @classmethod
    def remove_connection(cls, pid, connection):
        """Remove a connection from the pool, closing it if is open.

        :param str pid: The pool ID
        :param connection: The connection to remove
        :type connection: psycopg2.extensions.connection
        :raises: ConnectionNotFoundError

        """
        cls._ensure_pool_exists(pid)
        cls._pools[pid].remove(connection)

    @classmethod
    def set_idle_ttl(cls, pid, ttl):
        """Set the idle TTL for a pool, after which it will be destroyed.

        :param str pid: The pool id
        :param int ttl: The TTL for an idle pool

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            cls._pools[pid].set_idle_ttl(ttl)

    @classmethod
    def set_max_size(cls, pid, size):
        """Set the maximum number of connections for the specified pool

        :param str pid: The pool to set the size for
        :param int size: The maximum number of connections

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            cls._pools[pid].set_max_size(size)

    @classmethod
    def shutdown(cls):
        """Close all connections on in all pools"""
        for pid in list(cls._pools.keys()):
            cls._pools[pid].shutdown()
        LOGGER.info('Shutdown complete, all pooled connections closed')

    @classmethod
    def size(cls, pid):
        """Return the number of connections in the pool

        :param str pid: The pool id
        :rtype int

        """
        with cls._lock:
            cls._ensure_pool_exists(pid)
            return len(cls._pools[pid])

    @classmethod
    def _ensure_pool_exists(cls, pid):
        """Raise an exception if the pool has yet to be created or has been
        removed.

        :param str pid: The pool ID to check for
        :raises: KeyError

        """
        if pid not in cls._pools:
            raise KeyError('Pool %s has not been created' % pid)


class QueriesException(Exception):
    """Base Exception for all other Queries exceptions"""
    pass


class ConnectionException(QueriesException):
    def __init__(self, cid):
        self.cid = cid


class PoolException(QueriesException):
    def __init__(self, pid):
        self.pid = pid


class PoolConnectionException(PoolException):
    def __init__(self, pid, cid):
        self.pid = pid
        self.cid = cid


class ActivePoolError(PoolException):
    """Raised when removing a pool that has active connections"""
    def __str__(self):
        return 'Pool %s has at least one active connection' % self.pid


class ConnectionBusyError(ConnectionException):
    """Raised when trying to lock a connection that is already busy"""
    def __str__(self):
        return 'Connection %s is busy' % self.cid


class ConnectionNotFoundError(PoolConnectionException):
    """Raised if a specific connection is not found in the pool"""
    def __str__(self):
        return 'Connection %s not found in pool %s' % (self.cid, self.pid)


class NoIdleConnectionsError(PoolException):
    """Raised if a pool does not have any idle, open connections"""
    def __str__(self):
        return 'Pool %s has no idle connections' % self.pid


class PoolFullError(PoolException):
    """Raised when adding a connection to a pool that has hit max-size"""
    def __str__(self):
        return 'Pool %s is at its maximum capacity' % self.pid
