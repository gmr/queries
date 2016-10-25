"""
Tornado Session Adapter

Use Queries asynchronously within the Tornado framework.

Example Use:

.. code:: python

    class NameListHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession(pool_max_size=60)

        @gen.coroutine
        def get(self):
            data = yield self.session.query('SELECT * FROM names')
            if data:
                self.finish({'names': data.items()})
                data.free()
            else:
                self.set_status(500, 'Error querying the data')

"""
import logging
import socket

from psycopg2 import extensions
from psycopg2 import extras

from tornado import concurrent
from tornado import gen
from tornado import ioloop
import psycopg2

from queries import pool
from queries import results
from queries import session
from queries import utils

from queries import DEFAULT_URI
from queries import PYPY

LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_POOL_SIZE = 25


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
        self._cleanup(self.cursor, self._fd)


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
                 pool_max_size=DEFAULT_MAX_POOL_SIZE,
                 io_loop=None):
        """Connect to a PostgreSQL server using the module wide connection and
        set the isolation level.

        :param str uri: PostgreSQL connection URI
        :param psycopg2.extensions.cursor: The cursor type to use
        :param int pool_idle_ttl: How long idle pools keep connections open
        :param int pool_max_size: The maximum size of the pool to use
        :param tornado.ioloop.IOLoop io_loop: IOLoop instance to use

        """
        self._connections = dict()
        self._futures = dict()

        self._cursor_factory = cursor_factory
        self._ioloop = io_loop or ioloop.IOLoop.instance()
        self._pool_manager = pool.PoolManager.instance()
        self._uri = uri

        # Ensure the pool exists in the pool manager
        if self.pid not in self._pool_manager:
            self._pool_manager.create(self.pid, pool_idle_ttl, pool_max_size)

    @property
    def connection(self):
        """Do not use this directly with Tornado applications

        :return:
        """
        return None

    @property
    def cursor(self):
        return None

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
        return self._execute('callproc', name, args)

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
        return self._execute('execute', sql, parameters)

    def validate(self):
        """Validate the session can connect or has open connections to
        PostgreSQL

        :rtype: bool

        """
        future = concurrent.TracebackFuture()

        def on_connected(cf):
            if cf.exception():
                future.set_exception(cf.exception())
                return

            connection = cf.result()
            fd = connection.fileno()

            # The connection would have been added to the pool manager, free it
            self._pool_manager.free(self.pid, connection)
            self._ioloop.remove_handler(fd)

            if fd in self._connections:
                del self._connections[fd]
            if fd in self._futures:
                del self._futures[fd]

            # Return the success in validating the connection
            future.set_result(True)

        # Grab a connection to PostgreSQL
        self._ioloop.add_future(self._connect(), on_connected)

        # Return the future for the query result
        return future

    def _connect(self):
        """Connect to PostgreSQL, either by reusing a connection from the pool
        if possible, or by creating the new connection.

        :rtype: psycopg2.extensions.connection
        :raises: pool.NoIdleConnectionsError

        """
        future = concurrent.TracebackFuture()

        # Attempt to get a cached connection from the connection pool
        try:
            connection = self._pool_manager.get(self.pid, self)
            self._connections[connection.fileno()] = connection
            future.set_result(connection)

            # Add the connection to the IOLoop
            self._ioloop.add_handler(connection.fileno(),
                                     self._on_io_events,
                                     ioloop.IOLoop.WRITE)
        except pool.NoIdleConnectionsError:
            self._create_connection(future)

        return future

    def _create_connection(self, future):
        """Create a new PostgreSQL connection

        :param tornado.concurrent.Future future: future for new conn result

        """
        LOGGER.debug('Creating a new connection for %s', self.pid)

        # Create a new PostgreSQL connection
        kwargs = utils.uri_to_kwargs(self._uri)

        try:
            connection = self._psycopg2_connect(kwargs)
        except (psycopg2.Error, OSError, socket.error) as error:
            future.set_exception(error)
            return

        # Add the connection for use in _poll_connection
        fd = connection.fileno()
        self._connections[fd] = connection

        def on_connected(cf):
            """Invoked by the IOLoop when the future is complete for the
            connection

            :param Future cf: The future for the initial connection

            """
            if cf.exception():
                future.set_exception(cf.exception())

            else:

                try:
                    # Add the connection to the pool
                    LOGGER.debug('Connection established for %s', self.pid)
                    self._pool_manager.add(self.pid, connection)
                except (ValueError, pool.PoolException) as error:
                    LOGGER.exception('Failed to add %r to the pool', self.pid)
                    future.set_exception(error)
                    return

                self._pool_manager.lock(self.pid, connection, self)

                # Added in because psycopg2ct connects and leaves the
                # connection in a weird state: consts.STATUS_DATESTYLE,
                # returning from Connection._setup without setting the state
                # as const.STATUS_OK
                if PYPY:
                    connection.status = extensions.STATUS_READY

                # Register the custom data types
                self._register_unicode(connection)
                self._register_uuid(connection)

                # Set the future result
                future.set_result(connection)

        # Add a future that fires once connected
        self._futures[fd] = concurrent.TracebackFuture()
        self._ioloop.add_future(self._futures[fd], on_connected)

        # Add the connection to the IOLoop
        self._ioloop.add_handler(connection.fileno(),
                                 self._on_io_events,
                                 ioloop.IOLoop.WRITE)

    def _execute(self, method, query, parameters=None):
        """Issue a query asynchronously on the server, mogrifying the
        parameters against the sql statement and yielding the results
        as a :py:class:`Results <queries.tornado_session.Results>` object.

        This function reduces duplicate code for callproc and query by getting
        the class attribute for the method passed in as the function to call.

        :param str method: The method attribute to use
        :param str query: The SQL statement or Stored Procedure name
        :param list|dict parameters: A dictionary of query parameters
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
        future = concurrent.TracebackFuture()

        def on_connected(cf):
            """Invoked by the future returned by self._connect"""
            if cf.exception():
                future.set_exception(cf.exception())
                return

            # Get the psycopg2 connection object and cursor
            conn = cf.result()
            cursor = self._get_cursor(conn)

            def completed(qf):
                """Invoked by the IOLoop when the future has completed"""
                if qf.exception():
                    error = qf.exception()
                    LOGGER.debug('Cleaning cursor due to exception: %r', error)
                    self._exec_cleanup(cursor, conn.fileno())
                    future.set_exception(error)
                else:
                    value = Results(cursor, self._exec_cleanup, conn.fileno())
                    future.set_result(value)

            # Setup a callback to wait on the query result
            self._futures[conn.fileno()] = concurrent.TracebackFuture()

            # Add the future to the IOLoop
            self._ioloop.add_future(self._futures[conn.fileno()],
                                    completed)

            # Get the cursor, execute the query
            func = getattr(cursor, method)
            func(query, parameters)

        # Grab a connection to PostgreSQL
        self._ioloop.add_future(self._connect(), on_connected)

        # Return the future for the query result
        return future

    def _exec_cleanup(self, cursor, fd):
        """Close the cursor, remove any references to the fd in internal state
        and remove the fd from the ioloop.

        :param psycopg2.extensions.cursor cursor: The cursor to close
        :param int fd: The connection file descriptor

        """
        LOGGER.debug('Closing cursor and cleaning %s', fd)
        try:
            cursor.close()
        except (psycopg2.Error, psycopg2.Warning) as error:
            LOGGER.debug('Error closing the cursor: %s', error)

        self._pool_manager.free(self.pid, self._connections[fd])
        self._ioloop.remove_handler(fd)

        if fd in self._connections:
            del self._connections[fd]
        if fd in self._futures:
            del self._futures[fd]

    def _on_io_events(self, fd=None, events=None):
        """Invoked by Tornado's IOLoop when there are events for the fd

        :param int fd: The file descriptor for the event
        :param int events: The events raised

        """
        if fd not in self._connections:
            LOGGER.warning('Received IO event for non-existing connection')
            return
        self._poll_connection(fd)

    def _poll_connection(self, fd):
        """Check with psycopg2 to see what action to take. If the state is
        POLL_OK, we should have a pending callback for that fd.

        :param int fd: The socket fd for the postgresql connection

        """
        try:
            state = self._connections[fd].poll()
        except (OSError, socket.error) as error:
            self._ioloop.remove_handler(fd)
            if fd in self._futures and not self._futures[fd].done():
                self._futures[fd].set_exception(
                    psycopg2.OperationalError('Connection error (%s)' % error)
                )
        except (psycopg2.Error, psycopg2.Warning) as error:
            if fd in self._futures and not self._futures[fd].done():
                self._futures[fd].set_exception(error)
        else:
            if state == extensions.POLL_OK:
                if fd in self._futures and not self._futures[fd].done():
                    self._futures[fd].set_result(True)
            elif state == extensions.POLL_WRITE:
                self._ioloop.update_handler(fd, ioloop.IOLoop.WRITE)
            elif state == extensions.POLL_READ:
                self._ioloop.update_handler(fd, ioloop.IOLoop.READ)
            elif state == extensions.POLL_ERROR:
                self._ioloop.remove_handler(fd)
                if fd in self._futures and not self._futures[fd].done():
                    self._futures[fd].set_exception(
                        psycopg2.Error('Poll Error'))

    def _psycopg2_connect(self, kwargs):
        """Return a psycopg2 connection for the specified kwargs. Extend for
        use in async session adapters.

        :param dict kwargs: Keyword connection args
        :rtype: psycopg2.extensions.connection

        """
        kwargs['async'] = True
        return psycopg2.connect(**kwargs)
