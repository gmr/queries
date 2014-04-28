Session API
===========
The Session class allows for a unified (and simplified) view of interfacing with
a PostgreSQL database server.

Connection details are passed in as a PostgreSQL URI and connections are pooled
by default, allowing for reuse of connections across modules in the Python
runtime without having to pass around the object handle.

While you can still access the raw psycopg2_ :py:class:`~psycopg2.extensions.connection`
and :py:class:`~psycopg2.extensions.cursor` objects to provide ultimate flexibility
in how you use the :py:class:`queries.Session` object, there are convenience
methods designed to simplify the interaction with PostgreSQL.

For psycopg2_ functionality outside of what is exposed in Session, simply
use the :py:meth:`queries.Session.connection` or :py:meth:`queries.Session.cursor`
properties to gain access to either object just as you would in a program using
psycopg2_ directly.

Example Usage
-------------
The following example connects to the ``postgres`` database on ``localhost`` as
the ``postgres`` user and then queries a table, iterating over the results:

.. code:: python

    import queries

    with queries.Session('pgsql://postgres@localhost/postgres') as session:
        for row in session.query('SELECT * FROM table'):
            print row

Class Documentation
-------------------
.. autoclass:: queries.Session
    :members:

.. _psycopg2: https://pypi.python.org/pypi/psycopg2