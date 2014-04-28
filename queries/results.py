"""
Query or StoredProc Resultset

"""
import logging
import psycopg2

LOGGER = logging.getLogger(__name__)


class Results(object):
    """Class that is created for each query that allows for the use of query
    results...

    """
    def __init__(self, cursor, cleanup=None, fd=None):
        self.cursor = cursor
        self._cleanup = cleanup
        self._fd = fd

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __enter__(self):
        return self

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
        self._rewind()
        for row in self.cursor:
            yield row

    def __len__(self):
        """Return the number of rows that were returned from the query

        :rtype: int

        """
        return self.cursor.rowcount

    def __nonzero__(self):
        return bool(self.cursor.rowcount)

    def __repr__(self):
        return '<queries.%s rows=%s>' % (self.__class__.__name__, len(self))

    def as_dict(self):
        if not self.cursor.rowcount:
            return 0

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

    def items(self):
        """Return all of the rows that are in the result set.

        :rtype: list

        """
        self.cursor.scroll(0, 'absolute')
        return self.cursor.fetchall()

    def release(self):
        """Release the results, only used in async children"""
        LOGGER.warning("Released results in queries.Session")

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
