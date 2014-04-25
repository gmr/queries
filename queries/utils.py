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

PARSED = collections.namedtuple('Parsed',
                                'scheme,netloc,path,params,query,fragment,'
                                'username,password,hostname,port')

DEFAULT_HOSTNAME = 'localhost'
DEFAULT_PORT = 5432

KEYWORDS = ['connect_timeout',
            'client_encoding',
            'options',
            'application_name',
            'fallback_application_name',
            'keepalives',
            'keepalives_idle',
            'keepalives_interval',
            'keepalives_count',
            'sslmode',
            'requiressl',
            'sslcompression',
            'sslcert',
            'sslkey',
            'sslrootcert',
            'sslcrl',
            'requirepeer',
            'krbsrvname',
            'gsslib',
            'service']


def get_current_user():
    """Return the current username for the logged in user

    :rtype: str

    """
    return pwd.getpwuid(os.getuid())[0]


def parse_qs(query_string):
    """Return the parsed query string in a python2/3 agnostic fashion

    :param str query_string: The URI query string
    :rtype: dict

    """
    return _urlparse.parse_qs(query_string)


def uri_to_kwargs(uri):
    """Return a URI as kwargs for connecting to PostgreSQL with psycopg2,
    applying default values for non-specified areas of the URI.

    :param str uri: The connection URI
    :rtype: dict

    """
    parsed = urlparse(uri)
    default_user = get_current_user()
    kwargs = {'host': parsed.hostname or DEFAULT_HOSTNAME,
              'port': parsed.port or DEFAULT_PORT,
              'dbname': parsed.path[1:] or default_user,
              'user': parsed.username or default_user,
              'password': parsed.password}
    values = parse_qs(parsed.query)
    for k in [k for k in values if k in KEYWORDS]:
        kwargs[k] = values[k][0] if len(values[k]) == 1 else values[k]
        try:
            if kwargs[k].isdigit():
                kwargs[k] = int(kwargs[k])
        except AttributeError:
            pass
    return kwargs


def urlparse(url):
    """Parse the URL in a Python2/3 independent fashion.

    :param str url: The URL to parse
    :rtype: Parsed

    """
    value = 'http%s' % url[5:] if url[:5] == 'pgsql' else url
    parsed = _urlparse.urlparse(value)
    return PARSED(parsed.scheme.replace('http', 'pgsql'), parsed.netloc,
                  parsed.path, parsed.params, parsed.query, parsed.fragment,
                  parsed.username, parsed.password, parsed.hostname,
                  parsed.port)
