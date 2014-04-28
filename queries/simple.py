"""
Methods exposing a simpler to use API for interacting with PostgreSQL

"""
from queries.session import Session

from queries import DEFAULT_URI


def callproc(name, args=None, uri=DEFAULT_URI):
    """Call a stored procedure on the server and yield the results as a
    :py:class:`queries.Result` object.

    .. code:: python

        for row in session.callproc('now'):
            print row

    :param str name: The procedure name
    :param list args: The list of arguments to pass in
    :param str uri: The PostgreSQL connection URI
    :rtype: queries.Results

    """
    with Session(uri) as session:
        yield session.callproc(name, args)


def query(sql, parameters=None, uri=DEFAULT_URI):
    """A generator to issue a query on the server, mogrifying the
    parameters against the sql statement and returning the yield the results
    as a :py:class:`queries.Result` object.

    .. code:: python

        for row in queries.query('SELECT * FROM foo WHERE bar=%(bar)s',
                                 {'bar': 'baz'}):
          print row

    :param str sql: The SQL statement
    :param dict parameters: A dictionary of query parameters
    :param str uri: The PostgreSQL connection URI
    :rtype: queries.Results

    """
    with Session(uri) as session:
        yield session.query(sql, parameters)


def uri(host='localhost', port='5432', dbname='postgres', user='postgres',
        password=None):
    """Return a PostgreSQL connection URI for the specified values.

    :param str host: Host to connect to
    :param int port: Port to connect on
    :param str dbname: The database name
    :param str user: User to connect as
    :param str password: The password to use, None for no password
    :return str: The PostgreSQL connection URI

    """
    if password:
        return 'pgsql://%s:%s@%s:%i/%s' % (user, password, host, port, dbname)
    return 'pgsql://%s@%s:%i/%s' % (user, host, port, dbname)
