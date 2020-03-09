.. py:module:: queries.pool

Connection Pooling
==================
The :py:class:`PoolManager <queries.pool.PoolManager>` class provides top-level
access to the queries pooling mechanism, managing pools of connections by DSN in
instances of the :py:class:`Pool <queries.pool.Pool>` class. The connections are
represented by instances of the :py:class:`Connection <queries.pool.Connection>`
class. :py:class:`Connection <queries.pool.Connection>` holds the psycopg2
connection handle as well as lock information that lets the Pool and PoolManager
know when connections are busy.

These classes are managed automatically by the :py:class:`Session <queries.Session>`
and should rarely be interacted with directly.

If you would like to use the :py:class:`PoolManager <queries.pool.PoolManager>`
to shutdown all connections to PostgreSQL, either reference it by class or using
the :py:meth:`PoolManager.instance <queries.pool.PoolManager.instance>` method.

.. autoclass:: queries.pool.PoolManager
    :members:

.. autoclass:: queries.pool.Pool
    :members:

.. autoclass:: queries.pool.Connection
    :members:
