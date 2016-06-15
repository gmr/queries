Version History
===============
- 1.8.10 2016-06-14
  - Propagate PoolManager exceptions from TornadoSession (#20) - Fix by Dave Shawley
- 1.8.9 2015-11-11
  - Move to psycopg2cffi for PyPy support
- 1.7.5 2015-09-03
  - Dont let Session and TornadoSession share connections
- 1.7.1 2015-03-25
  - Fix TornadoSession's use of cleanup (#8) - Fix by Oren Itamar
- 1.7.0 2015-01-13
  - Implement :py:meth:`Pool.shutdown <queries.pool.Pool.shutdown>` and :py:meth:`PoolManager.shutdown <queries.pool.PoolManager.shutdown>` to
    cleanly shutdown all open, non-executing connections across a Pool or all pools. Update locks in Pool operations to ensure atomicity.
- 1.6.1 2015-01-09
  - Fixes an iteration error when closing a pool (#7) - Fix by  Chris McGuire
- 1.6.0 2014-11-20
  - Handle URI encoded password values properly
- 1.5.0 2014-10-07
  - Handle empty query results in the iterator (#4) - Fix by Den Teresh
- 1.4.0 2014-09-04
  - Address exception handling in tornado_session
