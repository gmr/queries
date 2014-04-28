Query Results
=============
Results from calls to :py:meth:`Session.query <queries.Session.query>` and
:py:meth:`Session.callproc <queries.Session.callproc>` are returned as an
instance of the :py:class:`Results <queries.Results>` class. The
:py:class:`Results <queries.Results>` class provides multiple ways to access
the information about a query and the data returned from PostgreSQL.

Examples
--------
The following examples illustrate the various behaviors that the
:py:class:`Results <queries.Results>` class implements:

**Using Results as an Iterator**

.. code:: python

    for row in session.query('SELECT * FROM foo'):
        print row

**Accessing an individual row by index**

.. code:: python

    results = session.query('SELECT * FROM foo')
    print results[1]  # Access the second row of the results

**Casting single row results as a dict**

.. code:: python

    results = session.query('SELECT * FROM foo LIMIT 1')
    print results.as_dict()

**Checking to see if a query was successful**

.. code:: python

    results = session.query("UPDATE foo SET bar='baz' WHERE qux='corgie'")
    if results:
        print 'Success'

**Checking the number of rows by using len(Results)**

.. code:: python

    results = session.query('SELECT * FROM foo')
    print '%i rows' % len(results)


Class Documentation
-------------------
.. autoclass:: queries.Results
    :members:
