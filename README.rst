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
- Support of Python 2.7+ and 3.4+
- PyPy support via psycopg2cffi_
- Asynchronous support for Tornado_
- Connection information provided by URI
- Query results delivered as a generator based iterators
- Automatically registered data-type support for UUIDs, Unicode and Unicode Arrays
- Ability to directly access psycopg2 ``connection`` and ``cursor`` objects
- Internal connection pooling

|Version| |Status| |Coverage| |License|

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
Queries provides a session based API for interacting with PostgreSQL.
Simply pass in the URI_ of the PostgreSQL server to connect to when creating
a session:

.. code:: python

    session = queries.Session("postgresql://postgres@localhost:5432/postgres")

Queries built-in connection pooling will re-use connections when possible,
lowering the overhead of connecting and reconnecting.

When specifying a URI, if you omit the username and database name to connect
with, Queries will use the current OS username for both. You can also omit the
URI when connecting to connect to localhost on port 5432 as the current OS user,
connecting to a database named for the current user. For example, if your
username is ``fred`` and you omit the URI when issuing ``queries.query`` the URI
that is constructed would be ``postgresql://fred@localhost:5432/fred``.

If you'd rather use individual values for the connection, the queries.uri()
method provides a quick and easy way to create a URI to pass into the various
methods.

.. code:: python

    >>> queries.uri("server-name", 5432, "dbname", "user", "pass")
    'postgresql://user:pass@server-name:5432/dbname'


Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Currently Queries uses the following environment variables for tweaking various
configuration values.  The supported ones are:

* ``QUERIES_MAX_POOL_SIZE`` - Modify the maximum size of the connection pool (default: 1)

Using the queries.Session class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To execute queries or call stored procedures, you start by creating an instance of the
``queries.Session`` class. It can act as a context manager, meaning you can
use it with the ``with`` keyword and it will take care of cleaning up after itself. For
more information on the ``with`` keyword and context managers, see PEP343_.

In addition to both the ``queries.Session.query`` and ``queries.Session.callproc``
methods that are similar to the simple API methods, the ``queries.Session`` class
provides access to the psycopg2 connection and cursor objects.

**Using queries.Session.query**

The following example shows how a ``queries.Session`` object can be used
as a context manager to query the database table:

.. code:: python

    >>> import pprint
    >>> import queries
    >>>
    >>> with queries.Session() as session:
    ...     for row in session.query('SELECT * FROM names'):
    ...         pprint.pprint(row)
    ...
    {'id': 1, 'name': u'Jacob'}
    {'id': 2, 'name': u'Mason'}
    {'id': 3, 'name': u'Ethan'}

**Using queries.Session.callproc**

This example uses ``queries.Session.callproc`` to execute a stored
procedure and then pretty-prints the single row results as a dictionary:

.. code:: python

    >>> import pprint
    >>> import queries
    >>> with queries.Session() as session:
    ...   results = session.callproc('chr', [65])
    ...   pprint.pprint(results.as_dict())
    ...
    {'chr': u'A'}

**Asynchronous Queries with Tornado**

In addition to providing a Pythonic, synchronous client API for PostgreSQL,
Queries provides a very similar asynchronous API for use with Tornado.
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
            results = yield self.session.query('SELECT * FROM names')
            self.finish({'data': results.items()})
            results.free()

    application = web.Application([
        (r"/", MainHandler),
    ])

    if __name__ == "__main__":
        application.listen(8888)
        ioloop.IOLoop.instance().start()

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
.. _URI: http://www.postgresql.org/docs/9.3/static/libpq-connect.html#LIBPQ-CONNSTRING
.. _pgsql_wrapper: https://pypi.python.org/pypi/pgsql_wrapper
.. _Tornado: http://tornadoweb.org
.. _PEP343: http://legacy.python.org/dev/peps/pep-0343/
.. _psycopg2cffi: https://pypi.python.org/pypi/psycopg2cffi

.. |Version| image:: https://img.shields.io/pypi/v/queries.svg?
   :target: https://pypi.python.org/pypi/queries

.. |Status| image:: https://img.shields.io/travis/gmr/queries.svg?
   :target: https://travis-ci.org/gmr/queries

.. |Coverage| image:: https://img.shields.io/codecov/c/github/gmr/queries.svg?
   :target: https://codecov.io/github/gmr/queries?branch=master

.. |License| image:: https://img.shields.io/github/license/gmr/queries.svg?
   :target: https://github.com/gmr/queries
