"""
Tornado Session Adapter

Use Queries asynchronously within the Tornado framework.

Example Use:

.. code:: python

    class ExampleHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self):
            data = yield self.session.query('SELECT * FROM names')
            self.finish({'data': data})

"""
import logging

from psycopg2 import extensions
from psycopg2 import extras
from tornado import gen
from tornado import ioloop
from tornado import stack_context
import psycopg2

from queries import pool
from queries import session
from queries import DEFAULT_URI

LOGGER = logging.getLogger(__name__)


class TornadoSession(session.Session):
    """Session class for Tornado asynchronous applications. Uses
    :py:func:`tornado.gen.coroutine` to wrap API methods for use in Tornado.

    Utilizes connection pooling to ensure that multiple concurrent asynchronous
    queries do not block each other. Heavily trafficked services will require
    a higher ``max_pool_size`` to allow for greater connection concurrency.

    .. Note:: Unlike :py:meth:`Session.query <queries.Session.query>` and
        :py:meth:`Session.callproc <queries.Session.callproc>`, the
        :py:meth:`TornadoSession.query <queries.TornadoSession.query>` and
        :py:meth:`TornadoSession.callproc <queries.TornadoSession.callproc>`
        methods are not iterators and will return the full result set using
        :py:meth:`cursor.fetchall`.

    :param str uri: PostgreSQL connection URI
    :param psycopg2.cursor: The cursor type to use
    :param bool use_pool: Use the connection pool
    :param int max_pool_size: Maximum number of connections for a single URI

    """
    def __init__(self,
                 uri=DEFAULT_URI,
                 cursor_factory=extras.RealDictCursor,
                 use_pool=True,
                 max_pool_size=pool.MAX_SIZE):
        """Connect to a PostgreSQL server using the module wide connection and
        set the isolation level.

        :param str uri: PostgreSQL connection URI
        :param psycopg2.extensions.cursor: The cursor type to use
        :param bool use_pool: Use the connection pool
        :param int max_pool_size: Max number of connections for a single URI

        """
        self._callbacks = dict()
        self._listeners = dict()
        self._connections = dict()
        self._commands = dict()
        self._cursor_factory = cursor_factory
        self._exceptions = dict()
        self._ioloop = ioloop.IOLoop.instance()
        self._uri = uri
        self._use_pool = use_pool

    @gen.coroutine
    def callproc(self, name, args=None):
        """Call a stored procedure asynchronously on the server, passing in the
        arguments to be passed to the stored procedure, returning the results
        as a tuple of row count and result set.

        :param str name: The stored procedure name
        :param list args: An optional list of procedure arguments
        :rtype: list

        """
        # Grab a connection, either new or out of the pool
        connection, fd, status = self._connect()

        # Add a callback for either connecting or waiting for the query
        self._callbacks[fd] = yield gen.Callback((self, fd))

        # Add the connection to the IOLoop
        self._ioloop.add_handler(connection.fileno(), self._on_io_events,
                                 ioloop.IOLoop.WRITE)

        # Maybe wait for the connection
        if status == self.SETUP and connection.poll() != extensions.POLL_OK:
            yield gen.Wait((self, fd))
            # Setup the callback for the actual query
            self._callbacks[fd] = yield gen.Callback((self, fd))

        # Get the cursor, execute the query and wait for the result
        cursor = self._get_cursor(connection)
        cursor.callproc(name, args)
        yield gen.Wait((self, fd))

        # If there was an exception, cleanup, then raise it
        if fd in self._exceptions and self._exceptions[fd]:
            error = self._exceptions[fd]
            self._exec_cleanup(cursor, fd)
            raise error

        # Attempt to get any result that's pending for the query
        try:
            result = cursor.fetchall()
        except psycopg2.ProgrammingError:
            result = []

        # Close the cursor and cleanup the references for this request
        self._exec_cleanup(cursor, fd)

        # Return the result if there are any
        raise gen.Return(result)

    @gen.coroutine
    def listen(self, channel, callback):
        """Listen for notifications from PostgreSQL on the specified channel,
        passing in a callback to receive the notifications.

        :param str channel: The channel to stop listening on
        :param method callback: The method to call on each notification

        """
        # Grab a connection, either new or out of the pool
        connection, fd, status = self._connect()

        # Add a callback for either connecting or waiting for the query
        self._callbacks[fd] = yield gen.Callback((self, fd))

        # Add the connection to the IOLoop
        self._ioloop.add_handler(connection.fileno(), self._on_io_events,
                                 ioloop.IOLoop.WRITE)

        # Maybe wait for the connection
        if status == self.SETUP and connection.poll() != extensions.POLL_OK:
            yield gen.Wait((self, fd))
            # Setup the callback for the actual query
            self._callbacks[fd] = yield gen.Callback((self, fd))

        # Get the cursor
        cursor = self._get_cursor(connection)

        # Add the channel and callback to the class level listeners
        self._listeners[channel] = (fd, cursor)

        # Send the LISTEN to PostgreSQL
        cursor.execute("LISTEN %s" % channel)

        # Loop while we have listeners and a channel
        while channel in self._listeners and self._listeners[channel]:

            # Wait for an event on that FD
            yield gen.Wait((self, fd))

            # Iterate through all of the notifications
            while connection.notifies:
                notify = connection.notifies.pop()
                callback(channel, notify.pid, notify.payload)

            # Set a new callback for the fd if we're not exiting
            if channel in self._listeners:
                self._callbacks[fd] = yield gen.Callback((self, fd))

    @gen.coroutine
    def query(self, sql, parameters=None):
        """Issue a query asynchronously on the server, mogrifying the
        parameters against the sql statement and yielding the results as a
        tuple of row count and result set.

        :param str sql: The SQL statement
        :param dict parameters: A dictionary of query parameters
        :return tuple: (row_count, rows)

        """
        # Grab a connection, either new or out of the pool
        connection, fd, status = self._connect()

        # Add a callback for either connecting or waiting for the query
        self._callbacks[fd] = yield gen.Callback((self, fd))

        # Add the connection to the IOLoop
        self._ioloop.add_handler(connection.fileno(), self._on_io_events,
                                 ioloop.IOLoop.WRITE)

        # Maybe wait for the connection
        if status == self.SETUP and connection.poll() != extensions.POLL_OK:
            yield gen.Wait((self, fd))
            # Setup the callback for the actual query
            self._callbacks[fd] = yield gen.Callback((self, fd))

        # Get the cursor, execute the query and wait for the result
        cursor = self._get_cursor(connection)
        cursor.execute(sql, parameters)
        yield gen.Wait((self, fd))

        # If there was an exception, cleanup, then raise it
        if fd in self._exceptions and self._exceptions[fd]:
            error = self._exceptions[fd]
            self._exec_cleanup(cursor, fd)
            raise error

        # Carry the row count to return to the caller
        row_count = cursor.rowcount

        # Attempt to get any result that's pending for the query
        try:
            result = cursor.fetchall()
        except psycopg2.ProgrammingError:
            result = []

        # Close the cursor and cleanup the references for this request
        self._exec_cleanup(cursor, fd)

        # Return the result if there are any
        raise gen.Return((row_count, result))

    @gen.coroutine
    def unlisten(self, channel):
        """Cancel a listening to notifications on a PostgreSQL notification
        channel.

        :param str channel: The channel to stop listening on

        """
        if channel not in self._listeners:
            raise ValueError("No listeners for specified channel")

        # Get the fd and cursor, then remove the listener
        fd, cursor = self._listeners[channel]
        del self._listeners[channel]

        # Call the callback waiting in the LISTEN loop
        self._callbacks[fd]((self, fd))

        # Create a callback, unlisten and wait for the result
        self._callbacks[fd] = yield gen.Callback((self, fd))
        cursor.execute("UNLISTEN %s;" % channel)
        yield gen.Wait((self, fd))

        # Close the cursor and cleanup the references for this request
        self._exec_cleanup(cursor, fd)

    def _connect(self):
        """Connect to PostgreSQL and setup a few variables and data structures
        to reduce code in the coroutine methods.

        :return tuple: psycopg2.extensions.connection, int, int

        """
        connection = super(TornadoSession, self)._connect()
        fd, status = connection.fileno(), connection.status

        # Add the connection for use in _poll_connection
        self._connections[fd] = connection

        return connection, fd, status

    def _exec_cleanup(self, cursor, fd):
        """Close the cursor, remove any references to the fd in internal state
        and remove the fd from the ioloop.

        :param psycopg2.extensions.cursor cursor: The cursor to close
        :param int fd: The connection file descriptor

        """
        cursor.close()
        if fd in self._exceptions:
            del self._exceptions[fd]
        if fd in self._callbacks:
            del self._callbacks[fd]
        if fd in self._connections:
            del self._connections[fd]
        self._ioloop.remove_handler(fd)

    def _get_cursor(self, connection):
        """Return a cursor for the given connection.

        :param psycopg2.extensions.connection connection: The connection to use
        :rtype: psycopg2.extensions.cursor

        """
        return connection.cursor(cursor_factory=self._cursor_factory)

    @gen.coroutine
    def _on_io_events(self, fd=None, events=None):
        """Invoked by Tornado's IOLoop when there are events for the fd

        :param int fd: The file descriptor for the event
        :param int events: The events raised

        """
        if fd not in self._connections:
            return
        self._poll_connection(fd)

    @gen.coroutine
    def _poll_connection(self, fd):
        """Check with psycopg2 to see what action to take. If the state is
        POLL_OK, we should have a pending callback for that fd.

        :param int fd: The socket fd for the postgresql connection

        """
        try:
            state = self._connections[fd].poll()
        except (psycopg2.Error, psycopg2.Warning) as error:
            self._exceptions[fd] = error
            yield self._callbacks[fd]((self, fd))
        else:
            if state == extensions.POLL_OK:
                yield self._callbacks[fd]((self, fd))
            elif state == extensions.POLL_WRITE:
                self._ioloop.update_handler(fd, ioloop.IOLoop.WRITE)
            elif state == extensions.POLL_READ:
                self._ioloop.update_handler(fd, ioloop.IOLoop.READ)
            elif state == extensions.POLL_ERROR:
                LOGGER.debug('Error')
                self._ioloop.remove_handler(fd)

    @property
    def connection(self):
        """The connection property is not supported in
        :py:class:`~queries.TornadoSession`.

        :rtype: None

        """
        return None

    @property
    def cursor(self):
        """The cursor property is not supported in
        :py:class:`~queries.TornadoSession`.

        :rtype: None

        """
        return None

    def _psycopg2_connect(self, kwargs):
        """Return a psycopg2 connection for the specified kwargs. Extend for
        use in async session adapters.

        :param dict kwargs: Keyword connection args
        :rtype: psycopg2.extensions.connection

        """
        kwargs['async'] = True
        with stack_context.NullContext():
            return psycopg2.connect(**kwargs)
