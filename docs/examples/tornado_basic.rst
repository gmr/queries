Basic Tornado Usage
===================
The following example implements a very basic RESTful API. The following DDL will
create the table used by the API:

.. code:: sql

    CREATE TABLE widgets (sku varchar(10) NOT NULL PRIMARY KEY,
                          name text NOT NULL,
                          qty integer NOT NULL);
