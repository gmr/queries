Using Queries
=============
Queries provides both a session based API and a stripped-down simple API for
interacting with PostgreSQL. If you're writing applications that will only have
one or two queries, the simple API may be useful. Instead of creating a session
object when using the simple API methods (:py:meth:`queries.query`  and
:py:meth:`queries.callproc`), this is done for you. Simply pass in your query
and the `URIs <http://www.postgresql.org/docs/9.3/static/libpq-connect.html#LIBPQ-CONNSTRING>`_
of the PostgreSQL server to connect to:

.. code:: python

    queries.query("SELECT now()", "postgresql://postgres@localhost:5432/postgres")

Queries built-in connection pooling will re-use connections when possible,
lowering the overhead of connecting and reconnecting. This is also true when
you're using Queries sessions in different parts of your application in the
same Python interpreter.

.. _connection-uris:

Connection URIs
---------------
When specifying a URI, if you omit the username and database name to connect
with, Queries will use the current OS username for both. You can also omit the
URI when connecting to connect to localhost on port 5432 as the current OS user,
connecting to a database named for the current user. For example, if your
username is *fred* and you omit the URI when issuing :py:meth:`queries.query`
the URI that is constructed would be ``postgresql://fred@localhost:5432/fred``.

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
    'postgresql://user:pass@server-name:5432/dbname'

Using the queries.Session class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To execute queries or call stored procedures, you start by creating an instance
of the :py:class:`queries.Session` class. It can act as a context manager,
meaning you can use it with the ``with`` keyword and it will take care of
cleaning up after itself. For more information on the ``with`` keyword and
context managers, see :pep:`343`.

In addition to both the :py:meth:`queries.Session.query` and
:py:meth:`queries.Session.callproc` methods that
are similar to the simple API methods, the :py:class:`queries.Session` class
provides access to the psycopg2 :py:class:`~psycopg2.extensions.connection` and
:py:class:`~psycopg2.extensions.cursor`  objects.

**Using queries.Session.query**

The following example shows how a :py:class:`queries.Session` object can be
used as a context manager to query the database table:

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

**Using queries.Session.callproc**

This example uses :py:meth:`queries.Session.callproc` to execute a stored
procedure and then pretty-prints the single row results as a dictionary:

.. code:: python

    >>> import pprint
    >>> import queries
    >>> with queries.Session() as session:
    ...   results = session.callproc('chr', [65])
    ...   pprint.pprint(results.as_dict())
    ...
    {'chr': u'A'}
