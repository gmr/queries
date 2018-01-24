import logging
import queries
from tornado import gen, ioloop, web


class ExampleHandler(web.RequestHandler):

    def initialize(self):
        self.session = queries.TornadoSession()

    @gen.coroutine
    def get(self):
        try:
            result = yield self.session.query('SELECT * FROM names')
        except queries.OperationalError as error:
            logging.error('Error connecting to the database: %s', error)
            raise web.HTTPError(503)

        self.finish({'data': result.items()})
        result.free()


application = web.Application([
    (r'/', ExampleHandler),
])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    application.listen(8888)
    ioloop.IOLoop.instance().start()
