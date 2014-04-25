"""
Utility functions for access to OS level info and URI parsing

"""
import collections
import os
import pwd
try:
    from urllib import parse as _urlparse
except ImportError:
    import urlparse as _urlparse

Parsed = collections.namedtuple('Parsed',
                                'scheme,netloc,path,params,query,fragment,'
                                'username,password,hostname,port')

DEFAULT_HOSTNAME = 'localhost'
DEFAULT_PORT = 5432
DEFAULT_DBNAME = 'postgres'
DEFAULT_USERNAME = 'postgres'

def get_current_user():
    """Return the current username for the logged in user

    :rtype: str

    """
    return pwd.getpwuid(os.getuid())[0]


def parse_qs(query_string):
    return _urlparse.parse_qs(query_string)


def uri_to_kwargs(uri):
    """Return a URI as kwargs for connecting to PostgreSQL with psycopg2,
    applying default values for non-specified areas of the URI.

    :param str uri: The connection URI
    :rtype: dict

    """
    parsed = urlparse(uri)
    default_user = get_current_user()
    return {'host': parsed.hostname or DEFAULT_HOSTNAME,
            'port': parsed.port or DEFAULT_PORT,
            'dbname': parsed.path[1:] or default_user,
            'user': parsed.username or default_user,
            'password': parsed.password}


def urlparse(url):
    value = 'http%s' % url[5:] if url[:5] == 'pgsql' else url
    parsed = _urlparse.urlparse(value)
    return Parsed(parsed.scheme.replace('http', 'pgsql'), parsed.netloc,
                  parsed.path, parsed.params, parsed.query, parsed.fragment,
                  parsed.username, parsed.password, parsed.hostname,
                  parsed.port)