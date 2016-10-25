"""The Session class allows for a unified (and simplified) view of
interfacing with a PostgreSQL database server.

Connection details are passed in as a PostgreSQL URI and connections are pooled
by default, allowing for reuse of connections across modules in the Python
runtime without having to pass around the object handle.

While you can still access the raw `psycopg2` connection and cursor objects to
provide ultimate flexibility in how you use the queries.Session object, there
are convenience methods designed to simplify the interaction with PostgreSQL.
For `psycopg2` functionality outside of what is exposed in Session, simply
use the Session.connection or Session.cursor properties to gain access to
either object just as you would in a program using psycopg2 directly.

Example usage:

.. code:: python

    import queries

    with queries.Session('pgsql://postgres@localhost/postgres') as session:
        for row in session.Query('SELECT * FROM table'):
            print row

"""
import hashlib
import logging

import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

from queries import pool
from queries import results
from queries import utils

LOGGER = logging.getLogger(__name__)

from queries import DEFAULT_URI
from queries import PYPY

DEFAULT_ENCODING = 'UTF8'


class Session(object):
    """The Session class allows for a unified (and simplified) view of
    interfacing with a PostgreSQL database server. The Session object can
    act as a context manager, providing automated cleanup and simple, Pythonic
    way of interacting with the object.

    :param str uri: PostgreSQL connection URI
    :param psycopg2.extensions.cursor: The cursor type to use
    :param int pool_idle_ttl: How long idle pools keep connections open
    :param int pool_max_size: The maximum size of the pool to use

    """
    _conn = None
    _cursor = None
    _tpc_id = None
    _uri = None

    # Connection status constants
    INTRANS = extensions.STATUS_IN_TRANSACTION
    PREPARED = extensions.STATUS_PREPARED
    READY = extensions.STATUS_READY
    SETUP = extensions.STATUS_SETUP

    # Transaction status constants
    TX_ACTIVE = extensions.TRANSACTION_STATUS_ACTIVE
    TX_IDLE = extensions.TRANSACTION_STATUS_IDLE
    TX_INERROR = extensions.TRANSACTION_STATUS_INERROR
    TX_INTRANS = extensions.TRANSACTION_STATUS_INTRANS
    TX_UNKNOWN = extensions.TRANSACTION_STATUS_UNKNOWN

    def __init__(self, uri=DEFAULT_URI,
                 cursor_factory=extras.RealDictCursor,
                 pool_idle_ttl=pool.DEFAULT_IDLE_TTL,
                 pool_max_size=pool.DEFAULT_MAX_SIZE):
        """Connect to a PostgreSQL server using the module wide connection and
        set the isolation level.

        :param str uri: PostgreSQL connection URI
        :param psycopg2.extensions.cursor: The cursor type to use
        :param int pool_idle_ttl: How long idle pools keep connections open
        :param int pool_max_size: The maximum size of the pool to use

        """
        self._pool_manager = pool.PoolManager.instance()
        self._uri = uri

        # Ensure the pool exists in the pool manager
        if self.pid not in self._pool_manager:
            self._pool_manager.create(self.pid, pool_idle_ttl, pool_max_size)

        self._conn = self._connect()
        self._cursor_factory = cursor_factory
        self._cursor = self._get_cursor(self._conn)
        self._autocommit()

    @property
    def backend_pid(self):
        """Return the backend process ID of the PostgreSQL server that this
        session is connected to.

        :rtype: int

        """
        return self._conn.get_backend_pid()

    def callproc(self, name, args=None):
        """Call a stored procedure on the server, returning the results in a
        :py:class:`queries.Results` instance.

        :param str name: The procedure name
        :param list args: The list of arguments to pass in
        :rtype: queries.Results
        :raises: queries.DataError
        :raises: queries.DatabaseError
        :raises: queries.IntegrityError
        :raises: queries.InternalError
        :raises: queries.InterfaceError
        :raises: queries.NotSupportedError
        :raises: queries.OperationalError
        :raises: queries.ProgrammingError

        """
        self._cursor.callproc(name, args)
        return results.Results(self._cursor)

    def close(self):
        """Explicitly close the connection and remove it from the connection
        pool if pooling is enabled. If the connection is already closed

        :raises: psycopg2.InterfaceError

        """
        if not self._conn:
            raise psycopg2.InterfaceError('Connection not open')
        LOGGER.info('Closing connection %r in %s', self._conn, self.pid)
        self._pool_manager.free(self.pid, self._conn)
        self._pool_manager.remove_connection(self.pid, self._conn)

        # Un-assign the connection and cursor
        self._conn, self._cursor = None, None

    @property
    def connection(self):
        """Return the current open connection to PostgreSQL.

        :rtype: psycopg2.extensions.connection

        """
        return self._conn

    @property
    def cursor(self):
        """Return the current, active cursor for the open connection.

        :rtype: psycopg2.extensions.cursor

        """
        return self._cursor

    @property
    def encoding(self):
        """Return the current client encoding value.

        :rtype: str

        """
        return self._conn.encoding

    @property
    def notices(self):
        """Return a list of up to the last 50 server notices sent to the client.

        :rtype: list

        """
        return self._conn.notices

    @property
    def pid(self):
        """Return the pool ID used for connection pooling.

        :rtype: str

        """
        return hashlib.md5(':'.join([self.__class__.__name__,
                                     self._uri]).encode('utf-8')).hexdigest()

    def query(self, sql, parameters=None):
        """A generator to issue a query on the server, mogrifying the
        parameters against the sql statement. Results are returned as a
        :py:class:`queries.Results` object which can act as an iterator and
        has multiple ways to access the result data.

        :param str sql: The SQL statement
        :param dict parameters: A dictionary of query parameters
        :rtype: queries.Results
        :raises: queries.DataError
        :raises: queries.DatabaseError
        :raises: queries.IntegrityError
        :raises: queries.InternalError
        :raises: queries.InterfaceError
        :raises: queries.NotSupportedError
        :raises: queries.OperationalError
        :raises: queries.ProgrammingError

        """
        self._cursor.execute(sql, parameters)
        return results.Results(self._cursor)

    def set_encoding(self, value=DEFAULT_ENCODING):
        """Set the client encoding for the session if the value specified
        is different than the current client encoding.

        :param str value: The encoding value to use

        """
        if self._conn.encoding != value:
            self._conn.set_client_encoding(value)

    def __del__(self):
        """When deleting the context, ensure the instance is removed from
        caches, etc.

        """
        self._cleanup()

    def __enter__(self):
        """For use as a context manager, return a handle to this object
        instance.

        :rtype: Session

        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """When leaving the context, ensure the instance is removed from
        caches, etc.

        """
        self._cleanup()

    def _autocommit(self):
        """Set the isolation level automatically to commit after every query"""
        self._conn.autocommit = True

    def _cleanup(self):
        """Remove the connection from the stack, closing out the cursor"""
        if self._cursor:
            LOGGER.debug('Closing the cursor on %s', self.pid)
            self._cursor.close()
            self._cursor = None

        if self._conn:
            LOGGER.debug('Freeing %s in the pool', self.pid)
            try:
                pool.PoolManager.instance().free(self.pid, self._conn)
            except pool.ConnectionNotFoundError:
                pass
            self._conn = None

    def _connect(self):
        """Connect to PostgreSQL, either by reusing a connection from the pool
        if possible, or by creating the new connection.

        :rtype: psycopg2.extensions.connection
        :raises: pool.NoIdleConnectionsError

        """
        # Attempt to get a cached connection from the connection pool
        try:
            connection = self._pool_manager.get(self.pid, self)
            LOGGER.debug("Re-using connection for %s", self.pid)
        except pool.NoIdleConnectionsError:
            if self._pool_manager.is_full(self.pid):
                raise

            # Create a new PostgreSQL connection
            kwargs = utils.uri_to_kwargs(self._uri)
            LOGGER.debug("Creating a new connection for %s", self.pid)
            connection = self._psycopg2_connect(kwargs)

            self._pool_manager.add(self.pid, connection)
            self._pool_manager.lock(self.pid, connection, self)

            # Added in because psycopg2ct connects and leaves the connection in
            # a weird state: consts.STATUS_DATESTYLE, returning from
            # Connection._setup without setting the state as const.STATUS_OK
            if PYPY:
                connection.reset()

            # Register the custom data types
            self._register_unicode(connection)
            self._register_uuid(connection)

        return connection

    def _get_cursor(self, connection, name=None):
        """Return a cursor for the given cursor_factory. Specify a name to
        use server-side cursors.

        :param connection: The connection to create a cursor on
        :type connection: psycopg2.extensions.connection
        :param str name: A cursor name for a server side cursor
        :rtype: psycopg2.extensions.cursor

        """
        cursor = connection.cursor(name=name,
                                   cursor_factory=self._cursor_factory)
        if name is not None:
            cursor.scrollable = True
            cursor.withhold = True
        return cursor

    def _psycopg2_connect(self, kwargs):
        """Return a psycopg2 connection for the specified kwargs. Extend for
        use in async session adapters.

        :param dict kwargs: Keyword connection args
        :rtype: psycopg2.extensions.connection

        """
        return psycopg2.connect(**kwargs)

    @staticmethod
    def _register_unicode(connection):
        """Register the cursor to be able to receive Unicode string.

        :type connection: psycopg2.extensions.connection
        :param connection: Where to register things

        """
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE,
                                          connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY,
                                          connection)

    @staticmethod
    def _register_uuid(connection):
        """Register the UUID extension from the psycopg2.extra module

        :type connection: psycopg2.extensions.connection
        :param connection: Where to register things

        """
        psycopg2.extras.register_uuid(conn_or_curs=connection)

    @property
    def _status(self):
        """Return the current connection status as an integer value.

        The status should match one of the following constants:

        - queries.Session.INTRANS: Connection established, in transaction
        - queries.Session.PREPARED: Prepared for second phase of transaction
        - queries.Session.READY: Connected, no active transaction

        :rtype: int

        """
        if self._conn.status == psycopg2.extensions.STATUS_BEGIN:
            return self.READY
        return self._conn.status
