Concurrent Queries in Tornado
=============================
The following example issues multiple concurrent queries in a single asynchronous
request and will wait until all queries are complete before progressing:

.. code:: python

    from tornado import gen, ioloop, web
    import queries


    class RequestHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        @gen.coroutine
        def get(self, *args, **kwargs):

            # Issue the three queries and wait for them to finish before progressing
            q1result, q2result = yield [self.session.query('SELECT * FROM foo'),
                                        self.session.query('SELECT * FROM bar'),
                                        self.session.query('INSERT INTO requests VALUES (%s, %s, %s)',
                                                           [self.remote_ip,
                                                            self.request_uri,
                                                            self.headers.get('User-Agent', '')])]
            # Close the connection
            self.finish({'q1result': q1result, 'q2result': q2result})

    if __name__ == "__main__":
        application = web.Application([
            (r"/", RequestHandler)
        ]).listen(8888)
        ioloop.IOLoop.instance().start()