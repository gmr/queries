"""
Methods exposing a simpler to use API for interacting with PostgreSQL

"""
from queries.session import Session

from queries import DEFAULT_URI


def callproc(name, parameters=None, uri=DEFAULT_URI):
    """Call a stored procedure on the server and return an iterator of the
    result set for easy access to the data.

    .. code:: python

        for row in session.callproc('now'):
            print row

    :param str name: The procedure name
    :param list parameters: The list of parameters to pass in
    :param str uri: The PostgreSQL connection URI
    :return: iterator

    """
    with Session(uri) as session:
        for row in session.callproc(name, parameters):
            yield row


def callproc_all(name, parameters=None, uri=DEFAULT_URI):
    """Call a stored procedure on the server and return the entire result set
    as a list.

    .. code:: python

        results = session.callproc('now'):

    :param str name: The procedure name
    :param list parameters: The list of parameters to pass in
    :param str uri: The PostgreSQL connection URI
    :return: list

    """
    with Session(uri) as session:
        return session.callproc_all(name, parameters)


def query(sql, parameters=None, uri=DEFAULT_URI):
    """A generator to issue a query on the server, mogrifying the
    parameters against the sql statement and returning the results as an
    iterator.

    .. code:: python

        for row in queries.query('SELECT * FROM foo WHERE bar=%(bar)s',
                                 {'bar': 'baz'}):
          print row

    :param str sql: The SQL statement
    :param dict parameters: A dictionary of query parameters
    :param str uri: The PostgreSQL connection URI
    :rtype: iterator

    """
    with Session(uri) as session:
        for row in session.query(sql, parameters):
            yield row



def query_all(sql, parameters=None, uri=DEFAULT_URI):
    """Issue a query to the server, mogrifying the parameters against the sql
    statement and return the results as a list.

    .. code:: python

        rows = queries.query('SELECT * FROM foo WHERE bar=%(bar)s',
                             {'bar': 'baz'}):

    :param str sql: The SQL statement
    :param dict parameters: A dictionary of query parameters
    :param str uri: The PostgreSQL connection URI
    :rtype: list

    """
    with Session(uri) as session:
        return session.query_all(sql, parameters)


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
