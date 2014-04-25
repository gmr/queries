Queries
=======
PostgreSQL database access simplified.

Queries is an opinionated wrapper for interfacing with PostgreSQL that offers
caching of connections and support for PyPy via psycopg2ct. Queries supports
Python versions 2.6+ and 3.2+.

The core `queries.Queries` class will automatically register support for UUIDs,
Unicode and Unicode arrays.

Without requiring any additional code, queries offers connection pooling that
allows for multiple modules in the same interpreter to use the same PostgreSQL
connection.

|Version| |Downloads| |Status|

Installation
------------
queries is available via pypi and can be installed with easy_install or pip:

pip install queries

Requirements
------------

- psycopg2 (for cpython support)
- psycopg2ct (for PyPy support)

Examples
--------

Executing a query and fetching data:

.. code:: python

    import queries

    uri = 'pgsql://postgres@localhost/postgres'
    for row in queries.execute(uri, 'SELECT 1 as value'):
        print(data['value'])

Creating a Postgres object for transactional behavior:

.. code:: python

    import queries

    uri = 'pgsql://postgres@localhost/postgres'
    pgsql = queries.Postgres(uri)
    pgsql.create_transaction()
    pgsql.callproc('SELECT foo FROM bar()')
    pgsql.commit()


.. |Version| image:: https://badge.fury.io/py/queries.svg?
   :target: http://badge.fury.io/py/queries

.. |Status| image:: https://travis-ci.org/gmr/queries.svg?branch=master
   :target: https://travis-ci.org/gmr/queries

.. |Downloads| image:: https://pypip.in/d/queries/badge.svg?
   :target: https://pypi.python.org/pypi/queries