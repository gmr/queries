"""
Tornado Session Adapter

Use Queries asynchronously within the Tornado framework.

"""
import logging

from psycopg2 import extensions
from psycopg2 import extras
from tornado import gen
from tornado import ioloop
from tornado import stack_context
import psycopg2

from queries import session
from queries import DEFAULT_URI

LOGGER = logging.getLogger(__name__)


class TornadoSession(session.Session):

    def __init__(self,
                 uri=DEFAULT_URI,
                 cursor_factory=extras.RealDictCursor,
                 use_pool=True):
        """Connect to a PostgreSQL server using the module wide connection and
        set the isolation level.

        :param str uri: PostgreSQL connection URI
        :param psycopg2.cursor: The cursor type to use
        :param bool use_pool: Use the connection pool

        """
        self._callbacks = dict()
        self._conn, self._cursor = None, None
        self._connections = dict()
        self._commands = dict()
        self._cursor_factory = cursor_factory
        self._exceptions = dict()
        self._ioloop = ioloop.IOLoop.instance()
        self._uri = uri
        self._use_pool = use_pool

    @gen.coroutine
    def callproc(self, name, parameters=None):

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
        cursor.callproc(name, parameters)
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
            result = None

        # Close the cursor and cleanup the references for this request
        self._exec_cleanup(cursor, fd)

        # Return the result if there are any
        raise gen.Return(result)

    @gen.coroutine
    def query(self, sql, parameters=None):

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

        # Attempt to get any result that's pending for the query
        try:
            result = cursor.fetchall()
        except psycopg2.ProgrammingError:
            result = None

        # Close the cursor and cleanup the references for this request
        self._exec_cleanup(cursor, fd)

        # Return the result if there are any
        raise gen.Return(result)

    def _connect(self):
        connection = super(TornadoSession, self)._connect()
        fd, status = connection.fileno(), connection.status

        # Add the connection for use in _poll_connection
        self._connections[fd] = connection

        return connection, fd, status

    def _exec_cleanup(self, cursor, fd):
        """Close the cursor, remove any references to the fd in internal state
        and remove the fd from the ioloop.

        :param psycopg2.cursor cursor: The cursor to close
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

        :param psycopg2._psycopg.connection connection: The connection to use
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

    def _psycopg2_connect(self, kwargs):
        """Return a psycopg2 connection for the specified kwargs. Extend for
        use in async session adapters.

        :param dict kwargs: Keyword connection args
        :rtype: psycopg2.connection

        """
        kwargs['async'] = True
        with stack_context.NullContext():
            return psycopg2.connect(**kwargs)
