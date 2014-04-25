"""
Connection Pooling

Implement basic connection pooling where connections are kept attached to this
module and re-used when the Queries object is created.

"""
import time

# Time-to-live in the pool
TTL = 60

# Connection caching constants
CLIENTS = 'clients'
HANDLE = 'handle'
LAST = 'last'
CONNECTIONS = dict()


def add_connection(uri, connection):
    """Add the connection to the module level connection dictionary. Will 
    return False if the connection is already in the pool.

    :param str uri: The connection URI
    :param psycopg2._psycopg.connection connection: PostgreSQL connection
    :returns bool: Connection was added to the pool

    """
    global CONNECTIONS
    if uri not in CONNECTIONS:
        CONNECTIONS[uri] = {CLIENTS: 1, HANDLE: connection, LAST: 0}
        return True
    return False


def check_for_unused_expired_connections():
    """Check the module level connection cache for connections without any
    clients and remove them if the TTL has passed.

    """
    global CONNECTIONS
    for uri in list(CONNECTIONS.keys()):
        if (not CONNECTIONS[uri][CLIENTS] and
            (time.time() > CONNECTIONS[uri][LAST] + TTL)):
            del CONNECTIONS[uri]


def get_connection(uri):
    """Check our global connection stack to see if we already have a
    connection with the same exact connection parameters and use it if so.

    :param str uri: The connection URI
    :rtype: psycopg2._psycopg.connection or None

    """
    check_for_unused_expired_connections()
    if uri in CONNECTIONS:
        CONNECTIONS[uri][CLIENTS] += 1
        return CONNECTIONS[uri][HANDLE]
    return None


def free_connection(uri):
    """Decrement our use counter for the hash and if it is the only one, delete
    the cached connection.

    :param str uri: The connection URI

    """
    global CONNECTIONS
    if uri in CONNECTIONS:
        CONNECTIONS[uri][CLIENTS] -= 1
        if not CONNECTIONS[uri][CLIENTS]:
            CONNECTIONS[uri][LAST] = int(time.time())


def remove_connection(uri):
    """Remove the cached connection, explicitly closing it.

    :param str uri: The connection URI

    """
    global CONNECTIONS
    if uri in CONNECTIONS:
        del CONNECTIONS[uri]
