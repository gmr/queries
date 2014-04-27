"""
Connection Pooling

Implement basic connection pooling where connections are kept attached to this
module and re-used when the Queries object is created.

"""
import collections
import logging
import time
import weakref

LOGGER = logging.getLogger(__name__)

# Max connections per-pool
MAX_CONNECTIONS = 10

# Time-to-live in the pool
TTL = 60

# Connection pooling data structures
Pools = dict()
Pool = collections.namedtuple('Pool', ['connections', 'sessions', 'last_use'])


def add_connection(pid, session, connection):
    """Add the connection to the module level connection dictionary. Will 
    return False if the connection is already in the pool.

    :param str pid: The pool id
    :param psycopg2._psycopg.connection connection: PostgreSQL connection
    :raises: ValueError

    """
    global Pools
    if pid not in Pools:
        Pools[pid] = Pool(set(), set(), 0)

    # Don't allow unbounded growth
    if len(Pools[pid].connections) > MAX_CONNECTIONS:
        raise ValueError('No room in the pool')

    Pools[pid].connections.add(connection)
    Pools[pid].sessions.add(weakref.ref(session))


def clean_pools():
    """Clean the Pools, pruning out stale references to sessions and close any
    pool connections when a pool is idle with no sessions. Empty pools will
    be removed from the Pools stack.

    """
    global Pools

    threshold = time.time() - TTL
    for pid in list(Pools.keys()):
        # Prune any stale references to session objects
        for session in list(Pools[pid].sessions):
            if session() is None:
                remove_session(pid, session)

        # Close connections when the pool is idle with no sessions
        if not Pools[pid].sessions and Pools[pid].last_use < threshold:
            [c.close() for c in Pools[pid].connections]
            [remove_connection(pid, c) for c in list(Pools[pid].connections)]

        # Remove the pool if there are no connections
        if not Pools[pid].connections:
            LOGGER.debug('Pool %s removed', pid)
            del Pools[pid]


def connection_in_pool(pid, connection):
    """Return True if the specific connection already exists in the pool

    :param str pid: The pool id
    :param psycopg2._psycopg.connection connection: Connection to check
    :rtype: bool

    """
    return bool([c for c in Pools[pid].connections if c == connection])


def get_connection(pid):
    """Return the first idle connection from the pool

    :param str pid: The pool to return the connection from
    :rtype: psycopg2._psycopg.connection|None

    """
    if not has_pool(pid):
        return None
    connections = [c for c in Pools[pid].connections if not c.isexecuting()]
    return connections[0] if connections else None


def has_idle_connection(pid):
    """Returns True if the connection has an idle connection that can be used.

    :param str pid: The pool id
    :rtype: bool

    """
    if not has_pool(pid):
        return False
    return bool([c for c in Pools[pid].connections if not c.isexecuting()])


def has_pool(pid):
    """Returns true if the pool exists

    :param str pid: the pool id to check
    :rtype: bool

    """
    return pid in Pools


def remove_connection(pid, connection):
    """Remove a connection from the pool

    :param str pid: The pool id
    :param psycopg2._psycopg.connection connection: Connection to remove

    """
    try:
        Pools[pid].connections.remove(connection)
    except KeyError:
        pass


def remove_session(pid, session):
    """Remove a session from the pool and if the session set is empty, set the
    last use time.

    :param str pid: The pool id
    :param queries.Session session: Session to remove

    """
    if pid not in Pools:
        return
    if not isinstance(session, weakref.ref):
        session = weakref.ref(session)
    try:
        Pools[pid].sessions.remove(session)
    except KeyError:
        pass
    if not Pools[pid].sessions:
        Pools[pid] = Pools[pid]._replace(last_use=int(time.time()))


def session_in_pool(pid, session):
    """Return True if the specific session reference already exists in the pool

    :param str pid: The pool id
    :param queries.Session session: Session to check
    :rtype: bool

    """
    session = weakref.ref(session)
    return bool([s for s in Pools[pid].sessions if session == s])
