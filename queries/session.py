"""PostgreSQL Class module



"""
import logging

import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

from queries import pool, PYPY

LOGGER = logging.getLogger(__name__)


class Session(object):
    """Core queries

    Uses a module level cache of connections to reduce overhead.

    """
    _from_pool = False

    # Connection status constants
    BEGIN = extensions.STATUS_BEGIN
    INTRANS = extensions.STATUS_IN_TRANSACTION
    PREPARED = extensions.STATUS_PREPARED
    READY = extensions.STATUS_READY

    # Transaction status constants
    TX_ACTIVE = extensions.TRANSACTION_STATUS_ACTIVE
    TX_IDLE = extensions.TRANSACTION_STATUS_IDLE
    TX_INERROR = extensions.TRANSACTION_STATUS_INERROR
    TX_INTRANS = extensions.TRANSACTION_STATUS_INTRANS
    TX_UNKNOWN = extensions.TRANSACTION_STATUS_UNKNOWN

    def __init__(self, uri,
                 cursor_factory=extras.RealDictCursor,
                 use_pool=True):
        """Connect to a PostgreSQL server using the module wide connection and
        set the isolation level.

        :param str uri: PostgreSQL connection URI
        :param psycopg2.cursor: The cursor type to use
        :param bool use_pool: Use the connection pool

        """
        self._uri = uri
        self._use_pool = use_pool
        self._conn = self._connect()
        self._cursor = self._get_cursor(cursor_factory)
        self._autocommit()

        # Don't re-register unicode or uuid
        if not use_pool or not self._from_pool:
            self._register_unicode()
            self._register_uuid()

    def __del__(self):
        """When deleting the context, ensure the instance is removed from
        caches, etc.

        """
        self._cleanup()

    def __enter__(self):
        """For use as a context manager, return a handle to this object
        instance.

        :rtype: PgSQL

        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """When leaving the context, ensure the instance is removed from
        caches, etc.

        """
        self._cleanup()

    @property
    def backend_pid(self):
        return self._conn.get_backend_pid()

    @property
    def connection(self):
        """Returns the psycopg2 PostgreSQL connection instance

        :rtype: psycopg2.connection

        """
        return self._conn

    @property
    def cursor(self):
        """Returns the cursor instance

        :rtype: psycopg2._psycopg.cursor

        """
        return self._cursor

    def cancel(self):
        self._conn.cancel()

    def commit(self):
        self._conn.commit()

    def listen(self, channel):
        pass

    @property
    def encoding(self):
        return self._conn.encoding

    def set_encoding(self, value='UTF-8'):
        self._conn.set_client_encoding(value)

    def rollback(self):
        self._conn.rollback()

    def create_transaction(self):
        self._conn.autocommit = False
        self._cursor.execute('')

    @property
    def notices(self):
        return self._conn.notices

    @property
    def status(self):
        return self._conn.status

    @property
    def tx_status(self):
        """Return the transaction status for the current connection.

        Values should be one of:

        - queries.Session.TX_IDLE: Idle without an active session
        - queries.Session.TX_ACTIVE: A command is currently in progress
        - queries.Session.TX_INTRANS: Idle in a valid transaction
        - queries.Session.TX_INERROR: Idle in a failed transaction
        - queries.Session.TX_UNKNOWN: Connection error

        :rtype: int

        """
        return self._conn.get_transaction_status()

    def close(self):
        """Explicitly close the connection and remove it from the connection
        cache.

        :raises: AssertionError

        """
        if not self._conn:
            raise AssertionError('Connection not open')
        self._conn.close()
        if self._use_pool:
            pool.remove_connection(self._uri)
        self._conn = None
        self._cursor = None

    def _autocommit(self):
        """Set the isolation level automatically to commit after every query"""
        self._conn.autocommit = True

    def _cleanup(self):
        """Remove the connection from the stack, closing out the cursor"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn:
            pool.free_connection(self._uri)
            self._conn = None

    def _connect(self):
        """Connect to PostgreSQL, either by reusing a connection from the pool
        if possible, or by creating the new connection.

        :rtype: psycopg2.connection

        """
        # Attempt to get a cached connection from the connection pool
        if self._use_pool:
            connection = pool.get_connection(self._uri)
            if connection:
                self._from_pool = True
                return connection

        # Create a new PostgreSQL connection
        connection = psycopg2.connect(self._uri)

        # Add it to the pool, if pooling is enabled
        if self._use_pool:
            pool.add_connection(self._uri, connection)

        # Added in because psycopg2ct connects and leaves the connection in
        # a weird state: consts.STATUS_DATESTYLE, returning from
        # Connection._setup without setting the state as const.STATUS_OK
        if PYPY:
            connection.reset()

        return connection

    def _get_cursor(self, cursor_factory):
        """Return a cursor for the given cursor_factory.

        :param psycopg2.cursor: The cursor type to use
        :rtype: psycopg2.extensions.cursor

        """
        return self._conn.cursor(cursor_factory=cursor_factory)

    def _register_unicode(self):
        """Register the cursor to be able to receive Unicode string.

        :param psycopg2.cursor: The cursor to add unicode support to

        """
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE,
                                          self._cursor)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY,
                                          self._cursor)

    def _register_uuid(self):
        """Register the UUID extension from psycopg2"""
        psycopg2.extras.register_uuid(self._conn)
