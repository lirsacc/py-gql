Getting Started
===============

This document will go over the basics of building a GraphQL server.
We will cover:

    1. Defining your types and schema
    2. Adding custom resolvers to your schema
    3. Executing client queries against the schema
    4. Exposing the schema behind an HTTP endpoint (using Flask)

If you haven’t done so already, please take a moment to :ref:`install
<installation>` py-gql before continuing.


Defining your schema
--------------------

The first step in creating a GraphQL server is defining the types and
schema that clients will be able to query. The GraphQL schema that we'll
implement for this example is as follow (using the schema definition language):


.. literalinclude:: getting-started/schema.graphql
   :language: graphql

The easiest way to build an executable schema for our server is through
:func:`py_gql.build_schema` which does so by consuming the SDL:

.. literalinclude:: getting-started/schema.py
   :language: python


Interacting with your data through resolver functions
-----------------------------------------------------

The schema as defined above isn't going to be very useful unless we have a way
to interact with our data. By default the runtime looks up fields as dict items
and object attributes of the root value you provide during execution. This works
for simple cases, but it is limited when running dynamic queries
(such as fetching a character by id like in our schema). In order to implement
custom field resolution you have to implement custom field resolvers.  This is
where your business logic and data access should live.

For this example we will use the following JSON dataset:

.. literalinclude:: getting-started/data.json
   :language: json

Let's implement our resolver functions:

.. literalinclude:: getting-started/resolvers.py
   :language: python

While we won't go into details concerning the resolvers signature we can already
note that they receive 3 positional arguments:

- The resolved parent value (The server root value for top-level fields)
- A context value which is where you provide any application specific value such
  as database connections, loggers, etc. In this case the ``db`` part of the
  context will be a mapping for each entry's id to itself.
- An info object which carries some data about the current execution and which we
  will not worry about for this example

While the GraphQL field arguments are passed as keyword arguments.

You will note that we haven't implemented any resolver for the field on the
``Character`` type. That is because the default behaviour is to look up field of
dictionnaries and objects which is sufficient here.


Executing queries against the schema
------------------------------------

Now that we have a valid schema, we just need to provide client queries for
execution. The execution is carried out by :func:`py_gql.graphql_blocking` and
consistst of 3 steps:

1. Parsing the client query and validating that it is a correct GraphQL document
2. Validating the query against the schema to verifying that it can be executed at all
3. Execute the query and surface any errors or return the data

The return value is an instance of :class:`py_gql.GraphQLResult` which can be
serialized using :meth:`py_gql.GraphQLResult.response`.

We will expose this behind an HTTP API using `Flask <http://flask.pocoo.org/>`_.

.. note::

    While the transport and serialization format depend on the application and
    are technically irrelevant to the GraphQL runtime itsefl; it is common
    to expose GraphQL APIs behind an HTTP server, traditionnaly under
    ``POST /graphql`` and JSON encoded.

.. literalinclude:: getting-started/flask.py
   :language: python

Pulling together all that we've seen so far you should have a working GraphQL
server that you can test using any HTTP client.

Using `httpie <https://httpie.org/>`_ for example (note that the response will
be reordered due to how httpie prints json, use ``--pretty=none`` to see the
raw response):

.. literalinclude:: getting-started/queries.txt


Complete code
-------------

.. literalinclude:: ../../examples/getting-started.py
   :language: python
