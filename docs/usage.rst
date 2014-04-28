Using Queries
=============
Queries provides both a session based API and a stripped-down simple API for
interacting with PostgreSQL. If you're writing applications that will only have
one or two queries, the simple API may be useful. Instead of creating a session
object when using the simple API methods (:py:meth:`queries.query`  and
:py:meth:`queries.callproc`), this is done for you. Simply pass in your query and
the `URIs <http://www.postgresql.org/docs/9.3/static/libpq-connect.html#LIBPQ-CONNSTRING>`_
of the PostgreSQL server to connect to:

.. code:: python

    queries.query("SELECT now()", "pgsql://postgres@localhost:5432/postgres")

Queries built-in connection pooling will re-use connections when possible,
lowering the overhead of connecting and reconnecting. This is also true when
you're using Queries sessions in different parts of your application in the same
Python interpreter.

.. _connection-uris:

Connection URIs
---------------
When specifying a URI, if you omit the username and database name to connect
with, Queries will use the current OS username for both. You can also omit the
URI when connecting to connect to localhost on port 5432 as the current OS user,
connecting to a database named for the current user. For example, if your
username is *fred* and you omit the URI when issuing :py:meth:`queries.query`
the URI that is constructed would be ``pgsql://fred@localhost:5432/fred``.

If you'd rather use individual values for the connection, the queries.uri()
method provides a quick and easy way to create a URI to pass into the various
methods.

.. autofunction:: queries.uri

Examples
--------
The following examples demonstrate various aspects of the Queries API. For more
detailed examples and documentation, visit the :doc:`simple`, :doc:`session`,
:doc:`results`, and :doc:`tornado_session` pages.

Using queries.uri to generate a URI from individual arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    >>> queries.uri("server-name", 5432, "dbname", "user", "pass")
    'pgsql://user:pass@server-name:5432/dbname'


Using the queries.query method to execute a query
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The :py:meth:`queries.query` method is one of the simple API methods intended
to provide quick, one-off access to executing queries on a PostgreSQL server.
It takes advantage of the Queries connection pool to reduce the overhead of
repeat usage in the same Python interpreter.

The following example uses the :ref:`default URI <connection-uris>` to execute a
query and iterate over the results:

.. code:: python

    >>> import pprint
    >>> import queries
    >>>
    >>> for row in queries.query('SELECT * FROM names'):
    ...     pprint.pprint(row)
    ...
    {'id': 1, 'name': u'Jacob'}
    {'id': 2, 'name': u'Mason'}
    {'id': 3, 'name': u'Ethan'}

Using the queries.callproc method to call a stored procedure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The :py:meth:`queries.callproc` method is one of the simple API methods intended
to provide quick, one-off access to calling stored-procedures. Like :py:meth:`queries.query`,
it takes advantage of the Queries connection pool to reduce the overhead of
repeat usage in the same Python interpreter.

.. code:: python

    >>> import pprint
    >>> import queries
    >>>
    >>> pprint.pprint(list(queries.callproc('now')))
    [{'now': datetime.datetime(2014, 4, 27, 15, 7, 18, 832480,
                               tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=-240, name=None))}

Using the queries.Session class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If your application is going to be performing multiple operations, you should use
the :py:class:`queries.Session` class. It can act as a context manager, meaning you can
use it with the ``with`` keyword and it will take care of cleaning up after itself. For
more information on the ``with`` keyword and context managers, see :pep:`343`.

In addition to both the :py:meth:`queries.Session.query` and
:py:meth:`queries.Session.callproc` methods that
are similar to the simple API methods, the :py:class:`queries.Session` class provides
access to the psycopg2 :py:class:`~psycopg2.extensions.connection` and
:py:class:`~psycopg2.extensions.cursor`  objects.  It also provides methods for
managing transactions and to the
`LISTEN/NOTIFY <http://www.postgresql.org/docs/9.3/static/sql-listen.html>`_
functionality provided by PostgreSQL.

The following example shows how a :py:class:`queries.Session` object can be used
as a context manager:

.. code:: python

    >>> import pprint
    >>> import queries
    >>>
    >>> with queries.Session() as s:
    ...     for row in s.query('SELECT * FROM names'):
    ...         pprint.pprint(row)
    ...
    {'id': 1, 'name': u'Jacob'}
    {'id': 2, 'name': u'Mason'}
    {'id': 3, 'name': u'Ethan'}
