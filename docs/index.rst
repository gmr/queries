Queries: PostgreSQL Simplified
==============================
*Queries* is a BSD licensed opinionated wrapper of the psycopg2_ library for
interacting with PostgreSQL.

|Version| |Downloads|

The popular psycopg2_ package is a full-featured python client. Unfortunately
as a developer, you're often repeating the same steps to get started with your
applications that use it. Queries aims to reduce the complexity of psycopg2
while adding additional features to make writing PostgreSQL client applications
both fast and easy.

*Key features include*:

- Simplified API
- Support of Python 2.6+ and 3.2+
- PyPy support via psycopg2ct
- Asynchronous support for Tornado_
- Connection information provided by URI
- Query results delivered as a generator based iterators
- Automatically registered data-type support for UUIDs, Unicode and Unicode Arrays
- Ability to directly access psycopg2_ :py:class:`~psycopg2.extensions.connection` and :py:class:`~psycopg2.extensions.cursor` objects
- Internal connection pooling

Installation
------------
Queries can be installed via the `Python Package Index <https://pypi.python.org/pypi/queries>`_ and
can be installed by running :command:`easy_install queries` or :command:`pip install queries`

When installing Queries, ``pip`` or ``easy_install`` will automatically install the proper
dependencies for your platform.

Contents
--------

.. toctree::
   :maxdepth: 1

   usage
   session
   results
   tornado_session
   pool
   examples/index.rst
   history

Issues
------
Please report any issues to the Github repo at `https://github.com/gmr/queries/issues <https://github.com/gmr/queries/issues>`_

Source
------
Queries source is available on Github at  `https://github.com/gmr/queries <https://github.com/gmr/queries>`_

|Status|

Inspiration
-----------
Queries is inspired by `Kenneth Reitz's <https://github.com/kennethreitz/>`_ awesome
work on `requests <http://docs.python-requests.org/en/latest/>`_.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _pypi: https://pypi.python.org/pypi/queries
.. _psycopg2: https://pypi.python.org/pypi/psycopg2
.. _URIs: http://www.postgresql.org/docs/9.3/static/libpq-connect.html#LIBPQ-CONNSTRING
.. _pgsql_wrapper: https://pypi.python.org/pypi/pgsql_wrapper
.. _Tornado: http://tornadoweb.org

.. |Version| image:: https://badge.fury.io/py/queries.svg?
   :target: http://badge.fury.io/py/queries

.. |Status| image:: https://travis-ci.org/gmr/queries.svg?branch=master
   :target: https://travis-ci.org/gmr/queries

.. |Downloads| image:: https://pypip.in/d/queries/badge.svg?
   :target: https://pypi.python.org/pypi/queries
