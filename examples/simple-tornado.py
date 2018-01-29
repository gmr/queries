import datetime
import logging

from queries import pool
import queries
from tornado import gen, ioloop, web


class ExampleHandler(web.RequestHandler):

    SQL = 'SELECT * FROM pg_stat_activity'

    @gen.coroutine
    def get(self):
        try:
            result = yield self.application.session.query(self.SQL)
        except queries.OperationalError as error:
            logging.error('Error connecting to the database: %s', error)
            raise web.HTTPError(503)

        rows = []
        for row in result.items():
            row = dict([(k, v.isoformat()
                         if isinstance(v, datetime.datetime) else v)
                        for k, v in row.items()])
            rows.append(row)
        result.free()
        self.finish({'pg_stat_activity': rows})


class ReportHandler(web.RequestHandler):

    @gen.coroutine
    def get(self):
        self.finish(pool.PoolManager.report())


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    application = web.Application([
        (r'/', ExampleHandler),
        (r'/report', ReportHandler)
    ], debug=True)
    application.session = queries.TornadoSession()
    application.listen(8000)
    ioloop.IOLoop.instance().start()
