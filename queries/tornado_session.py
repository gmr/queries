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
            results = yield self.session.query('SELECT * FROM names')
            self.finish({'data': results.items()})
            results.free()

"""
import logging

from psycopg2 import extensions
from psycopg2 import extras
from tornado import gen
from tornado import ioloop
from tornado import stack_context
import psycopg2

from queries import pool
from queries import results
from queries import session
from queries import utils
from queries import DEFAULT_URI
from queries import PYPY

LOGGER = logging.getLogger(__name__)


class Results(results.Results):
    """A TornadoSession specific :py:class:`queries.Results` class that adds
    the :py:meth:`Results.free <queries.tornado_session.Results.free>` method.
    The :py:meth:`Results.free <queries.tornado_session.Results.free>` method
    **must** be called to free the connection that the results were generated
    on. `Results` objects that are not freed will cause the connections to
    remain locked and your application will eventually run out of connections
    in the pool.

    The following examples illustrate the various behaviors that the
    ::py:class:`queries.Results <queries.tornado_session.Requests>` class
    implements:

    **Using Results as an Iterator**

    .. code:: python

        results = yield session.query('SELECT * FROM foo')
        for row in results
            print row
        results.free()

    **Accessing an individual row by index**

    .. code:: python

        results = yield session.query('SELECT * FROM foo')
        print results[1]  # Access the second row of the results
        results.free()

    **Casting single row results as a dict**

    .. code:: python

        results = yield session.query('SELECT * FROM foo LIMIT 1')
        print results.as_dict()
        results.free()

    **Checking to see if a query was successful**

    .. code:: python

        sql = "UPDATE foo SET bar='baz' WHERE qux='corgie'"
        results = yield session.query(sql)
        if results:
            print 'Success'
        results.free()

    **Checking the number of rows by using len(Results)**

    .. code:: python

        results = yield session.query('SELECT * FROM foo')
        print '%i rows' % len(results)
        results.free()

    """
    def __init__(self, cursor, cleanup, fd):
        self.cursor = cursor
        self._cleanup = cleanup
        self._fd = fd

    @gen.coroutine
    def free(self):
        """Release the results and connection lock from the TornadoSession
        object. This **must** be called after you finish processing the results
        from :py:meth:`TornadoSession.query <queries.TornadoSession.query>` or
        :py:meth:`TornadoSession.callproc <queries.TornadoSession.callproc>`
        or the connection will not be able to be reused by other asynchronous
        requests.

        """
        yield self._cleanup(self.cursor, self._fd)


class TornadoSession(session.Session):
    """Session class for Tornado asynchronous applications. Uses
    :py:func:`tornado.gen.coroutine` to wrap API methods for use in Tornado.

    Utilizes connection pooling to ensure that multiple concurrent asynchronous
    queries do not block each other. Heavily trafficked services will require
    a higher ``max_pool_size`` to allow for greater connection concurrency.

    :py:meth:`TornadoSession.query <queries.TornadoSession.query>` and
    :py:meth:`TornadoSession.callproc <queries.TornadoSession.callproc>` must
    call :py:meth:`Results.free <queries.tornado_session.Results.free>`

    :param str uri: PostgreSQL connection URI
    :param psycopg2.extensions.cursor: The cursor type to use
    :param int pool_idle_ttl: How long idle pools keep connections open
    :param int pool_max_size: The maximum size of the pool to use

    """
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
        self._callbacks = dict()
        self._connections = dict()
        self._exceptions = dict()
        self._listeners = dict()

        self._cursor_factory = cursor_factory
        self._ioloop = ioloop.IOLoop.instance()
        self._pool_manager = pool.PoolManager.instance()
        self._uri = uri

        # Ensure the pool exists in the pool manager
        if self.pid not in self._pool_manager:
            self._pool_manager.create(self.pid, pool_idle_ttl, pool_max_size)

    @gen.coroutine
    def callproc(self, name, args=None):
        """Call a stored procedure asynchronously on the server, passing in the
        arguments to be passed to the stored procedure, yielding the results
        as a :py:class:`Results <queries.tornado_session.Results>` object.

        You **must** free the results that are returned by this method to
        unlock the connection used to perform the query. Failure to do so
        will cause your Tornado application to run out of connections.

        :param str name: The stored procedure name
        :param list args: An optional list of procedure arguments
        :rtype: Results
        :raises: queries.DataError
        :raises: queries.DatabaseError
        :raises: queries.IntegrityError
        :raises: queries.InternalError
        :raises: queries.InterfaceError
        :raises: queries.NotSupportedError
        :raises: queries.OperationalError
        :raises: queries.ProgrammingError

        """
        conn = yield self._connect()

        # Setup a callback to wait on the query result
        self._callbacks[conn.fileno()] = yield gen.Callback((self,
                                                             conn.fileno()))

        # Get the cursor, execute the query and wait for the result
        cursor = self._get_cursor(conn)
        cursor.callproc(name, args)
        yield gen.Wait((self, conn.fileno()))

        # If there was an exception, cleanup, then raise it
        if (conn.fileno() in self._exceptions and
                self._exceptions[conn.fileno()]):
            error = self._exceptions[conn.fileno()]
            self._exec_cleanup(cursor, conn.fileno())
            raise error

        # Return the result if there are any
        cleanup = yield gen.Callback((self, self._exec_cleanup))
        raise gen.Return(Results(cursor, cleanup, conn.fileno()))

    @gen.coroutine
    def listen(self, channel, callback):
        """Listen for notifications from PostgreSQL on the specified channel,
        passing in a callback to receive the notifications.

        :param str channel: The channel to stop listening on
        :param method callback: The method to call on each notification

        """
        conn = yield self._connect()

        # Get the cursor
        cursor = self._get_cursor(conn)

        # Add the channel and callback to the class level listeners
        self._listeners[channel] = (conn.fileno(), cursor)

        # Send the LISTEN to PostgreSQL
        cursor.execute("LISTEN %s" % channel)

        # Loop while we have listeners and a channel
        while channel in self._listeners and self._listeners[channel]:

            # Wait for an event on that FD
            yield gen.Wait((self, conn.fileno()))

            # Iterate through all of the notifications
            while conn.notifies:
                notify = conn.notifies.pop()
                callback(channel, notify.pid, notify.payload)

            # Set a new callback for the fd if we're not exiting
            if channel in self._listeners:
                self._callbacks[conn.fileno()] = \
                    yield gen.Callback((self, conn.fileno()))

    @gen.coroutine
    def query(self, sql, parameters=None):
        """Issue a query asynchronously on the server, mogrifying the
        parameters against the sql statement and yielding the results
        as a :py:class:`Results <queries.tornado_session.Results>` object.

        You **must** free the results that are returned by this method to
        unlock the connection used to perform the query. Failure to do so
        will cause your Tornado application to run out of connections.

        :param str sql: The SQL statement
        :param dict parameters: A dictionary of query parameters
        :rtype: Results
        :raises: queries.DataError
        :raises: queries.DatabaseError
        :raises: queries.IntegrityError
        :raises: queries.InternalError
        :raises: queries.InterfaceError
        :raises: queries.NotSupportedError
        :raises: queries.OperationalError
        :raises: queries.ProgrammingError

        """
        conn = yield self._connect()

        # Setup a callback to wait on the query result
        self._callbacks[conn.fileno()] = yield gen.Callback((self,
                                                             conn.fileno()))

        # Get the cursor, execute the query and wait for the result
        cursor = self._get_cursor(conn)
        cursor.execute(sql, parameters)
        yield gen.Wait((self, conn.fileno()))
        del self._callbacks[conn.fileno()]

        # If there was an exception, cleanup, then raise it
        if (conn.fileno() in self._exceptions and
                self._exceptions[conn.fileno()]):
            error = self._exceptions[conn.fileno()]
            self._exec_cleanup(cursor, conn.fileno())
            raise error

        # Return the result if there are any
        raise gen.Return(Results(cursor, self._exec_cleanup, conn.fileno()))

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

    @gen.coroutine
    def _connect(self):
        """Connect to PostgreSQL, either by reusing a connection from the pool
        if possible, or by creating the new connection.

        :rtype: psycopg2.extensions.connection
        :raises: pool.NoIdleConnectionsError

        """
        # Attempt to get a cached connection from the connection pool
        try:
            connection = self._pool_manager.get(self.pid, self)

            self._connections[connection.fileno()] = connection
            self._callbacks[connection.fileno()] = None
            self._exceptions[connection.fileno()] = None

            # Add the connection to the IOLoop
            self._ioloop.add_handler(connection.fileno(), self._on_io_events,
                                     ioloop.IOLoop.WRITE)

        except pool.NoIdleConnectionsError:
            # "Block" while the pool is full
            while self._pool_manager.is_full(self.pid):
                LOGGER.warning('Pool %s is full, waiting 100ms', self.pid)
                timeout = yield gen.Callback((self, 'connect'))
                self._ioloop.add_timeout(100, timeout)
                yield gen.Wait((self, 'connect'))

            # Create a new PostgreSQL connection
            kwargs = utils.uri_to_kwargs(self._uri)
            connection = self._psycopg2_connect(kwargs)
            fd = connection.fileno()

            # Add the connection for use in _poll_connection
            self._connections[fd] = connection
            self._exceptions[fd] = None

            # Add a callback for either connecting or waiting for the query
            self._callbacks[fd] = yield gen.Callback((self, fd))

            # Add the connection to the IOLoop
            self._ioloop.add_handler(connection.fileno(), self._on_io_events,
                                     ioloop.IOLoop.WRITE)

            # Wait for the connection
            yield gen.Wait((self, fd))
            del self._callbacks[fd]

            # Add the connection to the pool
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

        raise gen.Return(connection)

    @gen.engine
    def _exec_cleanup(self, cursor, fd):
        """Close the cursor, remove any references to the fd in internal state
        and remove the fd from the ioloop.

        :param psycopg2.extensions.cursor cursor: The cursor to close
        :param int fd: The connection file descriptor

        """
        cursor.close()
        self._pool_manager.free(self.pid, self._connections[fd])

        if fd in self._exceptions:
            del self._exceptions[fd]
        if fd in self._callbacks:
            del self._callbacks[fd]
        if fd in self._connections:
            del self._connections[fd]

        self._ioloop.remove_handler(fd)
        raise gen.Return()

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
        return None

    @property
    def cursor(self):
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
