pgsql_wrapper
=============
An opinionated wrapper for interfacing with PostgreSQL that offers caching of
connections and support for PyPy via psycopg2ct. By default the PgSQL class
sets the cursor type to extras.DictCursor, and turns on both Unicode and UUID
support. In addition, isolation level is set to auto-commit.

As a convenience tool, pgsql_wrapper reduces the steps required in connecting to
and setting up the connections and cursors required to talk to PostgreSQL.

Without requiring any additional code, the module level caching of connections
allows for multiple modules in the same interpreter to use the same PostgreSQL
connection.

Requirements
------------

 - psycopg2
 - psycopg2ct (for PyPy support)

Example
-------

    import pgsql_wrapper

    HOST = 'localhost'
    PORT = 5432
    DBNAME = 'production'
    USER = 'www'


    connection = pgsql_wrapper.PgSQL(HOST, PORT, DBNAME, USER)
    connection.cursor.execute('SELECT 1 as value')
    data = connection.cursor.fetchone()
    print data['value']
