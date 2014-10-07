"""
query or callproc Results

"""
import logging
import psycopg2

LOGGER = logging.getLogger(__name__)


class Results(object):
    """The :py:class:`Results` class contains the results returned from
    :py:meth:`Session.query <queries.Session.query>` and
    :py:meth:`Session.callproc <queries.Session.callproc>`. It is able to act
    as an iterator and provides many different methods for accessing the
    information about and results from a query.

    :param psycopg2.extensions.cursor cursor: The cursor for the results

    """
    def __init__(self, cursor):
        self.cursor = cursor

    def __getitem__(self, item):
        """Fetch an individual row from the result set

        :rtype: mixed
        :raises: IndexError

        """
        try:
            self.cursor.scroll(item, 'absolute')
        except psycopg2.ProgrammingError:
            raise IndexError('No such row')
        else:
            return self.cursor.fetchone()

    def __iter__(self):
        """Iterate through the result set

        :rtype: mixed

        """
        if not self.cursor.rowcount:
            raise StopIteration

        self._rewind()
        for row in self.cursor:
            yield row

    def __len__(self):
        """Return the number of rows that were returned from the query

        :rtype: int

        """
        return self.cursor.rowcount if self.cursor.rowcount >= 0 else 0

    def __nonzero__(self):
        return bool(self.cursor.rowcount)

    def __repr__(self):
        return '<queries.%s rows=%s>' % (self.__class__.__name__, len(self))

    def as_dict(self):
        """Return a single row result as a dictionary. If the results contain
        multiple rows, a :py:class:`ValueError` will be raised.

        :return: dict
        :raises: ValueError

        """
        if not self.cursor.rowcount:
            return {}

        self._rewind()
        if self.cursor.rowcount == 1:
            return dict(self.cursor.fetchone())
        else:
            raise ValueError('More than one row')

    def count(self):
        """Return the number of rows that were returned from the query

        :rtype: int

        """
        return self.cursor.rowcount

    def free(self):
        """Used in asynchronous sessions for freeing results and their locked
        connections.

        """
        raise NotImplementedError

    def items(self):
        """Return all of the rows that are in the result set.

        :rtype: list

        """
        if not self.cursor.rowcount:
            return []

        self.cursor.scroll(0, 'absolute')
        return self.cursor.fetchall()

    @property
    def rownumber(self):
        """Return the current offset of the result set

        :rtype: int

        """
        return self.cursor.rownumber

    @property
    def query(self):
        """Return a read-only value of the query that was submitted to
        PostgreSQL.

        :rtype: str

        """
        return self.cursor.query

    @property
    def status(self):
        """Return the status message returned by PostgreSQL after the query
        was executed.

        :rtype: str

        """
        return self.cursor.statusmessage

    def _rewind(self):
        """Rewind the cursor to the first row"""
        self.cursor.scroll(0, 'absolute')
