.. py:module:: queries.tornado_session

TornadoSession Asynchronous API
===============================
Use a Queries Session asynchronously within the `Tornado <http://www.tornadoweb.org>`_ framework.

The :py:class:`TornadoSession <queries.TornadoSession>` class is optimized for
asynchronous concurrency. Each call to
:py:meth:`TornadoSession.callproc <queries.TornadoSession.callproc>` or
:py:meth:`TornadoSession.query <queries.TornadoSession.query>` grabs a free
connection from the connection pool and requires that the results that are r
returned as a
:py:class:`Results <queries.tornado_session.Results>` object are freed via the
:py:meth:`Results.free <queries.tornado_session.Results.free>` method. Doing
so will release the free the `Results` object data and release the lock on
the connection so that other queries are able to use the connection.

Example Use
-----------
The following :py:class:`~tornado.web.RequestHandler` example will return a
JSON document containing the query results.

.. code:: python

    import queries
    from tornado import gen, web

    class ExampleHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self):
            result = yield self.session.query('SELECT * FROM names')
            self.finish({'data': result.items()})
            result.free()

See the :doc:`examples/index` for more :py:meth:`~queries.TornadoSession` examples.

Class Documentation
-------------------
.. autoclass:: queries.tornado_session.TornadoSession
    :members:
    :inherited-members:

.. autoclass:: queries.tornado_session.Results
    :members:
    :inherited-members:
