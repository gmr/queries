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
from queries.session import Session

try:
    from queries.tornado_session import TornadoSession
except ImportError:
    TornadoSession = None

from queries.simple import callproc
from queries.simple import query
from queries.simple import uri

# For ease of access to different cursor types
from psycopg2.extras import DictCursor
from psycopg2.extras import NamedTupleCursor
from psycopg2.extras import RealDictCursor

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
