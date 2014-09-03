import datetime
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import queries
from tornado import testing


class SessionIntegrationTests(unittest.TestCase):

    def setUp(self):
        uri = queries.uri('localhost', 5432, 'postgres', 'postgres')
        try:
            self.session = queries.Session(uri, pool_max_size=10)
        except queries.OperationalError as error:
            raise unittest.SkipTest(str(error).split('\n')[0])

    def test_query_returns_results_object(self):
        self.assertIsInstance(self.session.query('SELECT 1 AS value'),
                              queries.Results)

    def test_query_result_value(self):
        result = self.session.query('SELECT 1 AS value')
        self.assertDictEqual(result.as_dict(), {'value': 1})

    def test_query_multirow_result_has_at_least_three_rows(self):
        result = self.session.query('SELECT * FROM pg_stat_database')
        self.assertGreaterEqual(result.count(), 3)

    def test_callproc_returns_results_object(self):
        timestamp = int(datetime.datetime.now().strftime('%s'))
        self.assertIsInstance(self.session.callproc('to_timestamp',
                                                    [timestamp]),
                              queries.Results)

    def test_callproc_mod_result_value(self):
        result = self.session.callproc('mod', [6, 4])
        self.assertEqual(6 % 4, result[0]['mod'])


class TornadoSessionIntegrationTests(testing.AsyncTestCase):

    def setUp(self):
        self.io_loop = self.get_new_ioloop()
        uri = queries.uri('localhost', 5432, 'postgres', 'postgres')
        try:
            self.session = queries.TornadoSession(uri,
                                                  pool_max_size=10,
                                                  io_loop=self.io_loop)
        except queries.OperationalError as error:
            raise unittest.SkipTest(str(error).split('\n')[0])

    @testing.gen_test
    def test_query_returns_results_object(self):
        result = yield self.session.query('SELECT 1 AS value')
        self.assertIsInstance(result, queries.Results)

    @testing.gen_test
    def test_query_result_value(self):
        result = yield self.session.query('SELECT 1 AS value')
        self.assertDictEqual(result.as_dict(), {'value': 1})

    @testing.gen_test
    def test_query_multirow_result_has_at_least_three_rows(self):
        result = yield self.session.query('SELECT * FROM pg_stat_database')
        self.assertGreaterEqual(result.count(), 3)

    @testing.gen_test
    def test_callproc_returns_results_object(self):
        timestamp = int(datetime.datetime.now().strftime('%s'))
        result = yield self.session.callproc('to_timestamp', [timestamp])
        self.assertIsInstance(result, queries.Results)

    @testing.gen_test
    def test_callproc_mod_result_value(self):
        result = yield self.session.callproc('mod', [6, 4])
        self.assertEqual(6 % 4, result[0]['mod'])
