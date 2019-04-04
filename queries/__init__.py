"""
Queries: PostgreSQL database access simplified

Queries is an opinionated wrapper for interfacing with PostgreSQL that offers
caching of connections and support for PyPy via psycopg2ct.

The core `queries.Queries` class will automatically register support for UUIDs,
Unicode and Unicode arrays.

"""
import logging
import sys

try:
    import psycopg2cffi
    import psycopg2cffi.extras
    import psycopg2cffi.extensions
except ImportError:
    pass
else:
    sys.modules['psycopg2'] = psycopg2cffi
    sys.modules['psycopg2.extras'] = psycopg2cffi.extras
    sys.modules['psycopg2.extensions'] = psycopg2cffi.extensions

from queries.results import Results
from queries.session import Session
try:
    from queries.tornado_session import TornadoSession
except ImportError:  # pragma: nocover
    TornadoSession = None
from queries.utils import uri

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

__version__ = '2.0.1'
version = __version__

# Add a Null logging handler to prevent logging output when un-configured
logging.getLogger('queries').addHandler(logging.NullHandler())
