TornadoSession Asynchronous API
===============================
Use a Queries Session asynchronously within the `Tornado <http://www.tornadoweb.org>`_ framework.

.. note:: Currently, due to the nature of how the connection pool is managed, transactions
    are not supported. Transaction support is expected to be added in a subsequent
    release. Queries executed are still atomic and will raise an exception if there are
    any errors.

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
            rows, data = yield self.session.query('SELECT * FROM names')
            self.finish({'data': data})

See the :doc:`examples/index` for more :py:meth:`~queries.TornadoSession` examples.

Class Documentation
-------------------
.. autoclass:: queries.TornadoSession
    :members:
