Basic Tornado Usage
===================
The following example implements a very basic RESTful API. The following DDL will
create the table used by the API:

.. code:: sql

    CREATE TABLE widgets (sku varchar(10) NOT NULL PRIMARY KEY,
                          name text NOT NULL,
                          qty integer NOT NULL);

The Tornado application provides two endpoints: /widget(/sku-value) and /widgets.
SKUs are set to be a 10 character value with the regex of ``[a-z0-9]{10}``. To
add a widget, call PUT on /widget, to update a widget call POST on /widget/[SKU].

.. code:: python

    from tornado import gen, ioloop, web
    import queries


    class WidgetRequestHandler(web.RequestHandler):
        """Handle the CRUD methods for a widget"""

        def initialize(self):
            self.session = queries.TornadoSession()

        def options(self, *args, **kwargs):
            self.set_header('Allow', ', '.join(['DELETE', 'GET', 'POST', 'PUT']))
            self.set_status(204)
            self.finish()

        @gen.coroutine
        def delete(self, *args, **kwargs):
            if 'sku' not in kwargs:
                self.set_status(403)
                self.finish({'error': 'missing required value: sku'})
            else:
                rows, data = yield self.session.query("DELETE FROM widgets WHERE sku=%(sku)s",
                                                      {'sku': kwargs['sku']})
                if not rows:
                    self.set_status(404)
                    self.finish({'error': 'SKU not found in system'})
                else:
                    self.set_status(204)
                    self.finish()

        @gen.coroutine
        def get(self, *args, **kwargs):
            if 'sku' not in kwargs:
                self.set_status(403)
                self.finish({'error': 'missing required value: sku'})
            rows, data = yield self.session.query("SELECT * FROM widgets WHERE sku=%(sku)s",
                                                  {'sku': kwargs['sku']})
            if not data:
                self.set_status(404)
                self.finish({'error': 'SKU not found in system'})
            else:
                self.finish(data[0])

        @gen.coroutine
        def post(self, *args, **kwargs):
            if 'sku' not in kwargs:
                self.set_status(403)
                self.finish({'error': 'missing required value: sku'})
            try:
                rows, result = yield self.session.query("UPDATE widgets SET name=%(name)s, qty=%(qty)s WHERE sku=%(sku)s",
                                                        {'sku': kwargs['sku'],
                                                         'name': self.get_argument('name'),
                                                         'qty': self.get_argument('qty')})
            except queries.DataError as error:
                self.set_status(404)
                self.finish({'error': {'error': error.pgerror.split('\n')[0][8:]}})
            else:
                if not rows:
                    self.set_status(404)
                    self.finish({'error': 'SKU not found in system'})
                else:
                    self.set_status(204)
                    self.finish()

        @gen.coroutine
        def put(self, *args, **kwargs):
            try:
                yield self.session.query("INSERT INTO widgets VALUES (%s, %s, %s)",
                                         [self.get_argument('sku'),
                                          self.get_argument('name'),
                                          self.get_argument('qty')])
            except (queries.DataError,
                    queries.IntegrityError) as error:
                self.set_status(409)
                self.finish({'error': {'error': error.pgerror.split('\n')[0][8:]}})
            else:
                self.set_status(201)
                self.finish()


    class WidgetsRequestHandler(web.RequestHandler):

        def initialize(self):
            self.session = queries.TornadoSession()

        def options(self, *args, **kwargs):
            self.set_header('Allow', ', '.join(['GET']))
            self.set_status(204)
            self.finish()

        @gen.coroutine
        def get(self, *args, **kwargs):
            rows, data = yield self.session.query("SELECT * FROM widgets ORDER BY sku")
            self.finish({'widgets': data})


    if __name__ == "__main__":
        application = web.Application([
            (r"/widget", WidgetRequestHandler),
            (r"/widget/(?P<sku>[a-z0-9]{10})", WidgetRequestHandler),
            (r"/widgets", WidgetsRequestHandler)
        ]).listen(8888)
        ioloop.IOLoop.instance().start()
