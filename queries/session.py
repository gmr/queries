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


"""
import hashlib
import logging

import psycopg2
from psycopg2 import extensions
from psycopg2 import extras

from queries import pool
from queries import utils

LOGGER = logging.getLogger(__name__)

from queries import DEFAULT_URI
from queries import PYPY

DEFAULT_ENCODING = 'UTF8'


class Session(object):
    """The Session class allows for a unified (and simplified) view of
    interfacing with a PostgreSQL database server. The Session object can
    act as a context manager, providing automated cleanup and simple, pythoic
    way of interacting with the object:

    .. code:: python

        import queries

        with queries.Session('pgsql://postgres@localhost/postgres') as session:
            for row in session.Query('SELECT * FROM table'):
                print row

    :param str uri: PostgreSQL connection URI
    :param psycopg2.cursor: The cursor type to use
    :param bool use_pool: Use the connection pool

    """
    _conn = None
    _cursor = None
    _cursor_factory = None
    _from_pool = False
    _tpc_id = None
    _uri = None
    _use_pool = True

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
        self._cursor_factory = cursor_factory
        self._cursor = self._get_cursor()
        self._autocommit()

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
        """Return the backend process ID of the PostgreSQL server that this
        session is connected to.

        :rtype: int

        """
        return self._conn.get_backend_pid()

    def close(self):
        """Explicitly close the connection and remove it from the connection
        pool if pooling is enabled.

        :raises: AssertionError

        """
        if not self._conn:
            raise AssertionError('Connection not open')

        if self._use_pool:
            pool.remove_connection(self.pid, self._conn)

        # Close the connection
        self._conn.close()
        self._conn, self._cursor = None, None

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

    @property
    def encoding(self):
        """The current client encoding value.

        :rtype: str

        """
        return self._conn.encoding

    @property
    def notices(self):
        """A list of up to the last 50 server notices sent to the client.

        :rtype: list

        """
        return self._conn.notices

    def set_encoding(self, value=DEFAULT_ENCODING):
        """Set the client encoding for the session if the value specified
        is different than the current client encoding.

        :param str value: The encoding value to use

        """
        if self._conn.encoding != value:
            self._conn.set_client_encoding(value)

    @property
    def status(self):
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

    # Querying, executing, copying, etc

    def callproc(self, name, parameters=None):
        """Call a stored procedure on the server and return an iterator of the
        result set for easy access to the data.

        .. code:: python

            for row in session.callproc('now'):
                print row

        To return the full set of rows in a single call, wrap the method with
        list:

        .. code:: python

            rows = list(session.callproc('now'))

        :param str name: The procedure name
        :param list parameters: The list of parameters to pass in
        :return: iterator

        """
        self._cursor.callproc(name, parameters)
        try:
            for record in self._cursor:
                yield record
        except psycopg2.ProgrammingError:
            return

    def query(self, sql, parameters=None):
        """A generator to issue a query on the server, mogrifying the
        parameters against the sql statement and returning the results as an
        iterator.

        .. code:: python

            for row in session.query('SELECT * FROM foo WHERE bar=%(bar)s',
                                     {'bar': 'baz'}):
              print row

        To return the full set of rows in a single call, wrap the method with
        list:

        .. code:: python

            rows = list(session.query('SELECT * FROM foo'))

        :param str sql: The SQL statement
        :param dict parameters: A dictionary of query parameters
        :rtype: iterator

        """
        self._cursor.execute(sql, parameters)
        try:
            for record in self._cursor:
                yield record
        except psycopg2.ProgrammingError:
            return

    # Listen Notify

    def listen(self, channel, callback=None):
        pass

    def notifications(self):
        pass

    # TPC Transaction Functionality

    def tx_begin(self):
        """Begin a new transaction"""
        # Ensure that auto-commit is off
        if self._conn.autocommit:
            self._conn.autocommit = False

    def tx_commit(self):
        self._conn.commit()

    def tx_rollback(self):
        self._conn.rollback()

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

    # Internal methods

    def _autocommit(self):
        """Set the isolation level automatically to commit after every query"""
        self._conn.autocommit = True

    def _cleanup(self):
        """Remove the connection from the stack, closing out the cursor"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._conn:
            self._conn = None

        if self._use_pool:
            pool.remove_session(self.pid, self)
            pool.clean_pools()

    def _connect(self):
        """Connect to PostgreSQL, either by reusing a connection from the pool
        if possible, or by creating the new connection.

        :rtype: psycopg2.connection

        """
        # Attempt to get a cached connection from the connection pool
        if self._use_pool and pool.has_idle_connection(self.pid):
            connection = pool.get_connection(self.pid)
            if connection:
                self._from_pool = True
                return connection

        # Create a new PostgreSQL connection
        kwargs = utils.uri_to_kwargs(self._uri)
        connection = self._psycopg2_connect(kwargs)

        # Add it to the pool, if pooling is enabled
        if self._use_pool:
            pool.add_connection(self.pid, self, connection)

        # Added in because psycopg2ct connects and leaves the connection in
        # a weird state: consts.STATUS_DATESTYLE, returning from
        # Connection._setup without setting the state as const.STATUS_OK
        if PYPY:
            connection.reset()

        # Register the custom data types
        self._register_unicode(connection)
        self._register_uuid(connection)

        return connection

    def _get_cursor(self):
        """Return a cursor for the given cursor_factory.

        :rtype: psycopg2.extensions.cursor

        """
        return self._conn.cursor(cursor_factory=self._cursor_factory)

    @property
    def pid(self):
        """Return a pool ID to be used with connection pooling

        :rtype: str

        """
        return str(hashlib.md5(self._uri.encode('utf-8')).digest())

    def _psycopg2_connect(self, kwargs):
        """Return a psycopg2 connection for the specified kwargs. Extend for
        use in async session adapters.

        :param dict kwargs: Keyword connection args
        :rtype: psycopg2.connection

        """
        return psycopg2.connect(**kwargs)

    @staticmethod
    def _register_unicode(connection):
        """Register the cursor to be able to receive Unicode string.

        :param psycopg2.connection connection: The connection to register on

        """
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE,
                                          connection)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY,
                                          connection)

    @staticmethod
    def _register_uuid(connection):
        """Register the UUID extension from the psycopg2.extra module

        :param psycopg2.connection connection: The connection to register on

        """
        psycopg2.extras.register_uuid(conn_or_curs=connection)
