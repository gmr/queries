"""
Methods exposing a simpler to use API for interacting with PostgreSQL

"""
import logging

from queries.session import Session

from queries import DEFAULT_URI


def execute(sql, uri=DEFAULT_URI):
    pass


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
