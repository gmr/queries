TornadoSession Asynchronous API
===============================
Use a Queries Session asynchronously within the `Tornado <http://www.tornadoweb.org>`_ framework.

Example Use
-----------
The following :py:class:`~tornado.web.RequestHandler` example will return a JSON document containing the query results.

.. code:: python

    import queries
    from tornado import gen, web

    class ExampleHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self):
            data = yield self.session.query('SELECT * FROM names')
            self.finish({'data': data})

Class Documentation
-------------------
.. autoclass:: queries.TornadoSession
    :members:
