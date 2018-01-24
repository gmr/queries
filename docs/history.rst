Version History
===============

1.11.0 2018-01-23
-----------------
 - Cleanup IOLoop and internal stack in ``TornadoSession`` on connection error.
   In the case of a connection error, the failure to do this caused CPU to peg
   @ 100% utilization looping on a non-existent file descriptor. Thanks to
   `cknave <https://github.com/cknave>`_ for his work on identifying the issue,
   proposing a fix, and writing a working test case.
 - Move the integration tests to use a local docker development environment
 -



1.10.4 2018-01-10
-----------------
 - Implement ``Results.__bool__`` to be explicit about Python 3 support.
 - Catch any exception raised when using TornadoSession and invoking the execute function in psycopg2 for exceptions raised prior to sending the query to Postgres.
   This could be psycopg2.Error, IndexError, KeyError, or who knows, it's not documented in psycopg2.

1.10.3 2017-11-01
-----------------
 - Remove the functionality from ``TornadoSession.validate`` and make it raise a ``DeprecationWarning``
 - Catch the ``KeyError`` raised when ``PoolManager.clean()`` is invoked for a pool that doesn't exist

1.10.2 2017-10-26
-----------------
 - Ensure the pool exists when executing a query in TornadoSession, the new timeout behavior prevented that from happening.

1.10.1 2017-10-24
-----------------
 - Use an absolute time in the call to ``add_timeout``

1.10.0 2017-09-27
-----------------
 - Free when tornado_session.Result is ``__del__'d`` without ``free`` being called.
 - Auto-clean the pool after Results.free TTL+1 in tornado_session.TornadoSession
 - Dont raise NotImplementedError in Results.free for synchronous use, just treat as a noop

1.9.1 2016-10-25
----------------
 - Add better exception handling around connections and getting the logged in user

1.9.0 2016-07-01
----------------
 - Handle a potential race condition in TornadoSession when too many simultaneous new connections are made and a pool fills up
 - Increase logging in various places to be more informative
 - Restructure queries specific exceptions to all extend off of a base QueriesException
 - Trivial code cleanup

1.8.10 2016-06-14
-----------------
 - Propagate PoolManager exceptions from TornadoSession (#20) - Fix by Dave Shawley

1.8.9 2015-11-11
----------------
 - Move to psycopg2cffi for PyPy support

1.7.5 2015-09-03
----------------
 - Don't let Session and TornadoSession share connections

1.7.1 2015-03-25
----------------
 - Fix TornadoSession's use of cleanup (#8) - Fix by Oren Itamar

1.7.0 2015-01-13
----------------
 - Implement :py:meth:`Pool.shutdown <queries.pool.Pool.shutdown>` and :py:meth:`PoolManager.shutdown <queries.pool.PoolManager.shutdown>` to
   cleanly shutdown all open, non-executing connections across a Pool or all pools. Update locks in Pool operations to ensure atomicity.

1.6.1 2015-01-09
----------------
 - Fixes an iteration error when closing a pool (#7) - Fix by  Chris McGuire

1.6.0 2014-11-20
-----------------
 - Handle URI encoded password values properly

1.5.0 2014-10-07
----------------
 - Handle empty query results in the iterator (#4) - Fix by Den Teresh

1.4.0 2014-09-04
----------------
 - Address exception handling in tornado_session
