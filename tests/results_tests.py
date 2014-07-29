"""
Tests for functionality in the results module

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import psycopg2

from queries import results


class ResultsTestCase(unittest.TestCase):

    def setUp(self):
        self.cursor = mock.MagicMock()
        self.obj = results.Results(self.cursor)

    def test_cursor_is_assigned(self):
        self.assertEqual(self.obj.cursor, self.cursor)

    def test_getitem_invokes_scroll(self):
        self.cursor.scroll = mock.Mock()
        self.cursor.fetchone = mock.Mock()
        _row = self.obj[1]
        self.cursor.scroll.assert_called_once_with(1, 'absolute')

    def test_getitem_raises_index_error(self):
        self.cursor.scroll = mock.Mock(side_effect=psycopg2.ProgrammingError)
        self.cursor.fetchone = mock.Mock()
        def get_row():
            return self.obj[1]
        self.assertRaises(IndexError, get_row)

    def test_getitem_invokes_fetchone(self):
        self.cursor.scroll = mock.Mock()
        self.cursor.fetchone = mock.Mock()
        _row = self.obj[1]
        self.cursor.fetchone.assert_called_once_with()

    def test_iter_rewinds(self):
        self.cursor.__iter__ = mock.Mock(return_value=iter([1, 2, 3]))
        with mock.patch.object(self.obj, '_rewind') as rewind:
            [x for x in self.obj]
            rewind.assert_called_once_with()

    def test_iter_iters(self):
        self.cursor.__iter__ = mock.Mock(return_value=iter([1, 2, 3]))
        with mock.patch.object(self.obj, '_rewind') as rewind:
            self.assertEqual([x for x in self.obj], [1, 2, 3])

    def test_rowcount_value(self):
        self.cursor.rowcount = 128
        self.assertEqual(len(self.obj), 128)

    def test_nonzero_false(self):
        self.cursor.rowcount = 0
        self.assertFalse(bool(self.obj))

    def test_nonzero_true(self):
        self.cursor.rowcount = 128
        self.assertTrue(bool(self.obj))

    def test_repr_str(self):
        self.cursor.rowcount = 128
        self.assertEqual(str(self.obj), '<queries.Results rows=128>')

    def test_as_dict_no_rows(self):
        self.cursor.rowcount = 0
        self.assertDictEqual(self.obj.as_dict(), {})

    def test_as_dict_rewinds(self):
        expectation = {'foo': 'bar', 'baz': 'qux'}
        self.cursor.rowcount = 1
        self.cursor.fetchone = mock.Mock(return_value=expectation)
        with mock.patch.object(self.obj, '_rewind') as rewind:
            result = self.obj.as_dict()
            rewind.assert_called_once_with()

    def test_as_dict_value(self):
        expectation = {'foo': 'bar', 'baz': 'qux'}
        self.cursor.rowcount = 1
        self.cursor.fetchone = mock.Mock(return_value=expectation)
        with mock.patch.object(self.obj, '_rewind') as rewind:
            self.assertDictEqual(self.obj.as_dict(), expectation)

    def test_as_dict_with_multiple_rows_raises(self):
        self.cursor.rowcount = 2
        with mock.patch.object(self.obj, '_rewind') as rewind:
            self.assertRaises(ValueError, self.obj.as_dict)

    def test_count_returns_rowcount(self):
        self.cursor.rowcount = 2
        self.assertEqual(self.obj.count(), 2)

    def test_free_raises_exception(self):
        self.assertRaises(NotImplementedError, self.obj.free)

    def test_items_invokes_scroll(self):
        self.cursor.scroll = mock.Mock()
        self.cursor.fetchall = mock.Mock()
        self.obj.items()
        self.cursor.scroll.assert_called_once_with(0, 'absolute')

    def test_items_invokes_fetchall(self):
        self.cursor.scroll = mock.Mock()
        self.cursor.fetchall = mock.Mock()
        self.obj.items()
        self.cursor.fetchall.assert_called_once_with()

    def test_rownumber_value(self):
        self.cursor.rownumber = 10
        self.assertEqual(self.obj.rownumber, 10)

    def test_query_value(self):
        self.cursor.query = 'SELECT * FROM foo'
        self.assertEqual(self.obj.query, 'SELECT * FROM foo')

    def test_status_value(self):
        self.cursor.statusmessage = 'Status message'
        self.assertEqual(self.obj.status, 'Status message')

    def test_rewind_invokes_scroll(self):
        self.cursor.scroll = mock.Mock()
        self.obj._rewind()
        self.cursor.scroll.assert_called_once_with(0, 'absolute')
