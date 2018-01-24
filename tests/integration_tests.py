import datetime
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from tornado import gen
from tornado import testing

import queries


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
        super(TornadoSessionIntegrationTests, self).setUp()
        self.session = queries.TornadoSession(queries.uri('localhost',
                                                          5432,
                                                          'postgres',
                                                          'postgres'),
                                              pool_max_size=10,
                                              io_loop=self.io_loop)

    @testing.gen_test
    def test_query_returns_results_object(self):
        try:
            result = yield self.session.query('SELECT 1 AS value')
        except queries.OperationalError:
            raise unittest.SkipTest('PostgreSQL is not running')
        self.assertIsInstance(result, queries.Results)
        result.free()

    @testing.gen_test
    def test_query_result_value(self):
        try:
            result = yield self.session.query('SELECT 1 AS value')
        except queries.OperationalError:
            raise unittest.SkipTest('PostgreSQL is not running')
        self.assertDictEqual(result.as_dict(), {'value': 1})
        result.free()

    @testing.gen_test
    def test_query_multirow_result_has_at_least_three_rows(self):
        try:
            result = yield self.session.query('SELECT * FROM pg_stat_database')
        except queries.OperationalError:
            raise unittest.SkipTest('PostgreSQL is not running')
        self.assertGreaterEqual(result.count(), 3)
        result.free()

    @testing.gen_test
    def test_callproc_returns_results_object(self):
        timestamp = int(datetime.datetime.now().strftime('%s'))
        try:
            result = yield self.session.callproc('to_timestamp', [timestamp])
        except queries.OperationalError:
            raise unittest.SkipTest('PostgreSQL is not running')
        self.assertIsInstance(result, queries.Results)
        result.free()

    @testing.gen_test
    def test_callproc_mod_result_value(self):
        try:
            result = yield self.session.callproc('mod', [6, 4])
        except queries.OperationalError:
            raise unittest.SkipTest('PostgreSQL is not running')
        self.assertEqual(6 % 4, result[0]['mod'])
        result.free()

    @testing.gen_test
    def test_polling_stops_after_connection_error(self):
        # Abort the test right away if postgres isn't running.
        good_uri = queries.uri('localhost', 5432, 'postgres', 'postgres')
        try:
            test_session = queries.Session(good_uri, pool_max_size=10)
            test_session.close()
        except queries.OperationalError as error:
            raise unittest.SkipTest(str(error).split('\n')[0])

        # Use an invalid user to force an OperationalError during connection
        bad_uri = queries.uri('localhost', 5432, 'invalid', 'invalid')
        session = queries.TornadoSession(bad_uri)

        self.count = 0
        real_poll_connection = session._poll_connection

        def count_polls(*args, **kwargs):
            self.count += 1
            real_poll_connection(*args, **kwargs)
        session._poll_connection = count_polls

        with self.assertRaises(queries.OperationalError):
            yield session.query('SELECT 1')
        yield gen.sleep(0.05)
        self.assertLess(self.count, 20)

    @testing.gen_test
    def test_invalid_query(self):
        try:
            with self.assertRaises(queries.ProgrammingError):
                yield self.session.query('INVALID QUERY')
        except queries.OperationalError:
            raise unittest.SkipTest('PostgreSQL is not running')
