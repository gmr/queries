Simple API
==========

The Queries simple API methods are meant for one off use, either in your apps
or directly in the Python interpreter. Connections maintained in a module level
pool, allowing for reuse of the methods without having to re-connect to PostgreSQL
within the same python interpreter.

Methods
-------

.. autofunction:: queries.query

.. autofunction:: queries.callproc
