"""
Utility functions for access to OS level info and URI parsing

"""
import collections
import logging
import os

# All systems do not support pwd module
try:
    import pwd
except ImportError:
    pwd = None
    import getpass

try:
    from urllib import parse as _urlparse
except ImportError:
    import urlparse as _urlparse
try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

LOGGER = logging.getLogger(__name__)

PARSED = collections.namedtuple('Parsed',
                                'scheme,netloc,path,params,query,fragment,'
                                'username,password,hostname,port')

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
    if pwd is None:
        return getpass.getuser()
    else:
        try:
            return pwd.getpwuid(os.getuid())[0]
        except KeyError as error:
            LOGGER.error('Could not get logged-in user: %s', error)


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
    password = unquote(parsed.password) if parsed.password else None
    kwargs = {'host': parsed.hostname,
              'port': parsed.port,
              'dbname': parsed.path[1:] or default_user,
              'user': parsed.username or default_user,
              'password': password}
    values = parse_qs(parsed.query)
    if 'host' in values:
        kwargs['host'] = values['host'][0]
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
    value = 'http%s' % url[5:] if url[:5] == 'postgresql' else url
    parsed = _urlparse.urlparse(value)

    # Python 2.6 hack
    if not parsed.query and '?' in parsed.path:
        path, query = parsed.path.split('?')
    else:
        path, query = parsed.path, parsed.query

    hostname = parsed.hostname if parsed.hostname else ''
    return PARSED(parsed.scheme.replace('http', 'postgresql'),
                  parsed.netloc,
                  path,
                  parsed.params,
                  query,
                  parsed.fragment,
                  parsed.username,
                  parsed.password,
                  hostname.replace('%2f', '/'),
                  parsed.port)
