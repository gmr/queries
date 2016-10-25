"""
Queries: PostgreSQL database access simplified

Queries is an opinionated wrapper for interfacing with PostgreSQL that offers
caching of connections and support for PyPy via psycopg2ct.

The core `queries.Queries` class will automatically register support for UUIDs,
Unicode and Unicode arrays.

"""
__version__ = '1.9.1'
version = __version__

import logging
import platform

# Import PyPy compatibility
PYPY = False
target = platform.python_implementation()
if target == 'PyPy':  # pragma: no cover
    import psycopg2cffi.compat
    psycopg2cffi.compat.register()
    PYPY = True

# Add a Null logging handler to prevent logging output when un-configured
try:
    from logging import NullHandler
except ImportError:  # pragma: no cover
    class NullHandler(logging.Handler):
        """Python 2.6 does not have a NullHandler"""
        def emit(self, record):
            """Emit a record

            :param record record: The record to emit

            """
            pass

logging.getLogger('queries').addHandler(NullHandler())

# Defaults
DEFAULT_URI = 'postgresql://localhost:5432'

# Mappings to queries classes and methods
from queries.results import Results
from queries.session import Session

try:
    from queries.tornado_session import TornadoSession
except ImportError:  # pragma: no cover
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
    if port:
        host = '%s:%s' % (host, port)
    if password:
        return 'postgresql://%s:%s@%s/%s' % (user, password, host, dbname)
    return 'postgresql://%s@%s/%s' % (user, host, dbname)


# For ease of access to different cursor types
from psycopg2.extras import DictCursor
from psycopg2.extras import NamedTupleCursor
from psycopg2.extras import RealDictCursor
from psycopg2.extras import LoggingCursor
from psycopg2.extras import MinTimeLoggingCursor

# Expose exceptions so clients do not need to import psycopg2 too
from psycopg2 import Warning
from psycopg2 import Error
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
