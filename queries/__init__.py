"""
Queries: PostgreSQL database access simplified

Queries is an opinionated wrapper for interfacing with PostgreSQL that offers
caching of connections and support for PyPy via psycopg2ct.

The core `queries.Queries` class will automatically register support for UUIDs,
Unicode and Unicode arrays.

"""
__version__ = '1.2.0'
version = __version__

import logging
import platform

# Import PyPy compatibility
PYPY = False
target = platform.python_implementation()
if target == 'PyPy':
    from psycopg2ct import compat
    compat.register()
    PYPY = True

# Add a Null logging handler to prevent logging output when un-configured
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """Python 2.6 does not have a NullHandler"""
        def emit(self, record):
            """Emit a record

            :param record record: The record to emit

            """
            pass

logging.getLogger('queries').addHandler(NullHandler())

# Defaults
DEFAULT_URI = 'pgsql://localhost:5432'

# Mappings to queries classes and methods
from queries.results import Results
from queries.session import Session

try:
    from queries.tornado_session import TornadoSession
except ImportError:
    TornadoSession = None


def uri(host='localhost', port=5432, dbname='postgres', user='postgres',
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


# For ease of access to different cursor types
from psycopg2.extras import DictCursor
from psycopg2.extras import NamedTupleCursor
from psycopg2.extras import RealDictCursor
from psycopg2.extras import LoggingCursor
from psycopg2.extras import MinTimeLoggingCursor

# Expose exceptions so clients do not need to import psycopg2 too
from psycopg2 import DataError
from psycopg2 import DatabaseError
from psycopg2 import IntegrityError
from psycopg2 import InterfaceError
from psycopg2 import InternalError
from psycopg2 import NotSupportedError
from psycopg2 import OperationalError
from psycopg2 import ProgrammingError
from psycopg2.extensions import QueryCanceledError
from psycopg2.extensions import TransactionRollbackError
