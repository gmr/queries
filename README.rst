Queries: PostgreSQL Simplified
==============================

*Queries* is a BSD licensed opinionated wrapper of the psycopg2_ library for
interacting with PostgreSQL.

The popular psycopg2_ package is a full-featured python client. Unfortunately
as a developer, you're often repeating the same steps to get started with your
applications that use it. Queries aims to reduce the complexity of psycopg2
while adding additional features to make writing PostgreSQL client applications
both fast and easy. Check out the `Usage`_ section below to see how easy it can be.

Key features include:

- Simplified API
- Support of Python 2.6+ and 3.2+
- PyPy support via psycopg2ct
- Asynchronous support for Tornado_
- Connection information provided by URI
- Query results delivered as a generator based iterators
- Automatically registered data-type support for UUIDs, Unicode and Unicode Arrays
- Ability to directly access psycopg2 ``connection`` and ``cursor`` objects
- Internal connection pooling

|Version| |Downloads| |Status|

Documentation
-------------
Documentation is available at https://queries.readthedocs.org

Installation
------------
Queries is available via pypi_ and can be installed with easy_install or pip:

.. code:: bash

    pip install queries

Usage
-----
Queries provides both a session based API and a stripped-down simple API for
interacting with PostgreSQL. If you're writing applications that will only have
one or two queries, the simple API may be useful. Instead of creating a session
object when using the simple API methods (``queries.query()`` and
``queries.callproc()``), this is done for you. Simply pass in your query and
the URIs_ of the PostgreSQL server to connect to:

.. code:: python

    queries.query("SELECT now()", "pgsql://postgres@localhost:5432/postgres")

Queries built-in connection pooling will re-use connections when possible,
lowering the overhead of connecting and reconnecting. This is also true when
you're using Queries sessions in different parts of your application in the same
Python interpreter.

When specifying a URI, if you omit the username and database name to connect
with, Queries will use the current OS username for both. You can also omit the
URI when connecting to connect to localhost on port 5432 as the current OS user,
connecting to a database named for the current user. For example, if your
username is ``fred`` and you omit the URI when issuing ``queries.query`` the URI
that is constructed would be ``pgsql://fred@localhost:5432/fred``.

If you'd rather use individual values for the connection, the queries.uri()
method provides a quick and easy way to create a URI to pass into the various
methods.

.. code:: python

    >>> queries.uri("server-name", 5432, "dbname", "user", "pass")
    'pgsql://user:pass@server-name:5432/dbname'

Here are a few examples of using the Queries simple API:

1. Executing a query and fetching data using the default URI:

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

2. Calling a stored procedure, returning the iterator results as a list:

.. code:: python

    >>> import pprint
    >>> import queries
    >>>
    >>> pprint.pprint(list(queries.callproc('now')))
    [{'now': datetime.datetime(2014, 4, 27, 15, 7, 18, 832480,
                               tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=-240, name=None))}

If your application is going to be performing multiple operations, you should use
the ``queries.Session`` class. It can act as a context manager, meaning you can
use it with the ``with`` keyword and it will take care of cleaning up after itself.

In addition to both the ``Session.query()`` and  ``Session.callproc()`` methods that
are similar to the simple API methods, the ``queries.Session`` class provides
access to the psycopg2 connection and cursor objects. It also provides methods
for managing transactions and to the LISTEN/NOTIFY functionality provided by
PostgreSQL. For full documentation around the Session class, see the
documentation_. The following example shows how a ``queries.Session`` object can
be used as a context manager.

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

In addition to providing a Pythonic, synchronous client API for PostgreSQL,
Queries provides a very similar asynchronous API for use with Tornado [1]_.
The only major difference API difference between ``queries.TornadoSession`` and
``queries.Session`` is the ``TornadoSession.query`` and ``TornadoSession.callproc``
methods return the entire result set instead of acting as an iterator over
the results. The following example uses ``TornadoSession.query`` in an asynchronous
Tornado_ web application to send a JSON payload with the query result set.

.. code:: python

    from tornado import gen, ioloop, web
    import queries

    class MainHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self):
            rows, data = yield self.session.query('SELECT * FROM names')
            self.finish({'data': data})


    application = web.Application([
        (r"/", MainHandler),
    ])

    if __name__ == "__main__":
        application.listen(8888)
        ioloop.IOLoop.instance().start()

.. [1] Simple API methods are not asynchronous and should not be used in an asynchronous Tornado application.

Inspiration
-----------
Queries is inspired by `Kenneth Reitz's <https://github.com/kennethreitz/>`_ awesome
work on `requests <http://docs.python-requests.org/en/latest/>`_.

History
-------
Queries is a fork and enhancement of pgsql_wrapper_, which can be found in the
main GitHub repository of Queries as tags prior to version 1.2.0.

.. _pypi: https://pypi.python.org/pypi/queries
.. _psycopg2: https://pypi.python.org/pypi/psycopg2
.. _documentation: https://queries.readthedocs.org
.. _URIs: http://www.postgresql.org/docs/9.3/static/libpq-connect.html#LIBPQ-CONNSTRING
.. _pgsql_wrapper: https://pypi.python.org/pypi/pgsql_wrapper
.. _Tornado: http://tornadoweb.org

.. |Version| image:: https://badge.fury.io/py/queries.svg?
   :target: http://badge.fury.io/py/queries

.. |Status| image:: https://travis-ci.org/gmr/queries.svg?branch=master
   :target: https://travis-ci.org/gmr/queries

.. |Downloads| image:: https://pypip.in/d/queries/badge.svg?
   :target: https://pypi.python.org/pypi/queries