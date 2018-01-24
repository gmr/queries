Basic TornadoSession Usage
==========================
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
            """Setup a queries.TornadoSession object to use when the RequestHandler
            is first initialized.

            """
            self.session = queries.TornadoSession()

        def options(self, *args, **kwargs):
            """Let the caller know what methods are supported

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            self.set_header('Allow', ', '.join(['DELETE', 'GET', 'POST', 'PUT']))
            self.set_status(204)  # Successful request, but no data returned
            self.finish()

        @gen.coroutine
        def delete(self, *args, **kwargs):
            """Delete a widget from the database

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            # We need a SKU, if it wasn't passed in the URL, return an error
            if 'sku' not in kwargs:
                self.set_status(403)
                self.finish({'error': 'missing required value: sku'})

            # Delete the widget from the database by SKU
            else:
                results = yield self.session.query("DELETE FROM widgets WHERE sku=%(sku)s",
                                                   {'sku': kwargs['sku']})
                if not results:
                    self.set_status(404)
                    self.finish({'error': 'SKU not found in system'})
                else:
                    self.set_status(204)  # Success, but no data returned
                    self.finish()

                # Free the results and release the connection lock from session.query
                results.free()

        @gen.coroutine
        def get(self, *args, **kwargs):
            """Fetch a widget from the database

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            # We need a SKU, if it wasn't passed in the URL, return an error
            if 'sku' not in kwargs:
                self.set_status(403)
                self.finish({'error': 'missing required value: sku'})

            # Fetch a row from the database for the SKU
            else:
                results = yield self.session.query("SELECT * FROM widgets WHERE sku=%(sku)s",
                                                   {'sku': kwargs['sku']})

                # No rows returned, send a 404 with a JSON error payload
                if not results:
                    self.set_status(404)
                    self.finish({'error': 'SKU not found in system'})

                # Send back the row as a JSON object
                else:
                    self.finish(results.as_dict())

                # Free the results and release the connection lock from session.query
                results.free()

        @gen.coroutine
        def post(self, *args, **kwargs):
            """Update a widget in the database

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            # We need a SKU, if it wasn't passed in the URL, return an error
            if 'sku' not in kwargs:
                self.set_status(403)
                self.finish({'error': 'missing required value: sku'})

            # Update the widget in the database by SKU
            else:

                sql = "UPDATE widgets SET name=%(name)s, qty=%(qty)s WHERE sku=%(sku)s"
                try:
                    results = yield self.session.query(sql,
                                                       {'sku': kwargs['sku'],
                                                        'name': self.get_argument('name'),
                                                        'qty': self.get_argument('qty')})

                    # Free the results and release the connection lock from session.query
                    results.free()

                # DataError is raised when there's a problem with the data passed in
                except queries.DataError as error:
                    self.set_status(409)
                    self.finish({'error': {'error': error.pgerror.split('\n')[0][8:]}})

                else:
                    # No rows means there was no record updated
                    if not results:
                        self.set_status(404)
                        self.finish({'error': 'SKU not found in system'})

                    # The record was updated
                    else:
                        self.set_status(204)  # Success, but not returning data
                        self.finish()

        @gen.coroutine
        def put(self, *args, **kwargs):
            """Add a widget to the database

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            try:
                results = yield self.session.query("INSERT INTO widgets VALUES (%s, %s, %s)",
                                                   [self.get_argument('sku'),
                                                    self.get_argument('name'),
                                                    self.get_argument('qty')])

                # Free the results and release the connection lock from session.query
                results.free()
            except (queries.DataError,
                    queries.IntegrityError) as error:
                self.set_status(409)
                self.finish({'error': {'error': error.pgerror.split('\n')[0][8:]}})
            else:
                self.set_status(201)
                self.finish()


    class WidgetsRequestHandler(web.RequestHandler):
        """Return a list of all of the widgets in the database"""

        def initialize(self):
            """Setup a queries.TornadoSession object to use when the RequestHandler
            is first initialized.

            """
            self.session = queries.TornadoSession()

        def options(self, *args, **kwargs):
            """Let the caller know what methods are supported

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            self.set_header('Allow', ', '.join(['GET']))
            self.set_status(204)
            self.finish()

        @gen.coroutine
        def get(self, *args, **kwargs):
            """Get a list of all the widgets from the database

            :param list args: URI path arguments passed in by Tornado
            :param list args: URI path keyword arguments passed in by Tornado

            """
            results = yield self.session.query('SELECT * FROM widgets ORDER BY sku')

            # Tornado doesn't allow you to return a list as a JSON result by default
            self.finish({'widgets': results.items()})

            # Free the results and release the connection lock from session.query
            results.free()


    if __name__ == "__main__":
        application = web.Application([
            (r"/widget", WidgetRequestHandler),
            (r"/widget/(?P<sku>[a-zA-Z0-9]{10})", WidgetRequestHandler),
            (r"/widgets", WidgetsRequestHandler)
        ]).listen(8888)
        ioloop.IOLoop.instance().start()
