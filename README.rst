Queries
=======
PostgreSQL database access simplified.

Queries is an opinionated wrapper for interfacing with PostgreSQL that offers
caching of connections and support for PyPy via psycopg2ct. Queries supports
Python versions 2.6+ and 3.2+. Additionally, Queries provides an asynchronous
interface to PostgreSQL for Tornado_.

The core `queries.Queries` class will automatically register support for UUIDs,
Unicode and Unicode arrays.

Without requiring any additional code, queries offers connection pooling that
allows for multiple modules in the same interpreter to use the same PostgreSQL
connection.

|Version| |Downloads| |Status|

Documentation
-------------
Documentation is available at https://queries.readthedocs.org

Installation
------------
queries is available via pypi and can be installed with easy_install or pip:

.. code:: bash

    pip install queries

Requirements
------------

- psycopg2 (for cpython support)
- psycopg2ct (for PyPy support)

Examples
--------

Executing a query and fetching data, connecting by default to `localhost` as
the current user with a database matching the username:

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

Calling a stored procedure, returning the iterator results as a list:

.. code:: python

    >>> import pprint
    >>> import queries
    >>>
    >>> pprint.pprint(list(queries.callproc('now')))
    [{'now': datetime.datetime(2014, 4, 27, 15, 7, 18, 832480,
                               tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=-240, name=None))}

Using the Session object as a context manager:

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

Using in a Tornado RequestHandler:

.. code:: python

    from tornado import gen, ioloop, web
    import queries

    class MainHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self):
            data = yield self.session.query('SELECT * FROM names')
            self.finish({'data': data})


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

.. _pgsql_wrapper: https://pypi.python.org/pypi/pgsql_wrapper

.. _tornado: http://tornadoweb.org

.. |Version| image:: https://badge.fury.io/py/queries.svg?
   :target: http://badge.fury.io/py/queries

.. |Status| image:: https://travis-ci.org/gmr/queries.svg?branch=master
   :target: https://travis-ci.org/gmr/queries

.. |Downloads| image:: https://pypip.in/d/queries/badge.svg?
   :target: https://pypi.python.org/pypi/queries