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
implement for this example is as follow (using the `schema definition language
<https://github.com/graphql/graphql-spec/pull/90>`_):


.. literalinclude:: getting-started/schema.graphql
    :language: graphql

The easiest way to build an executable schema for our server is through
:func:`py_gql.build_schema` which does so by consuming the SDL. This is often
referred to as a *schema first* approach to schema definition, as opposed to *code
first* where we'd build a schema from Python objects.

.. literalinclude:: getting-started/schema.py
    :language: python


Interacting with your data through resolver functions
-----------------------------------------------------

The schema as defined above isn't going to be very useful unless we have a way
to interact with our data.

For this example we will use the following JSON dataset:

.. literalinclude:: getting-started/data.json
    :language: json

Let's implement our resolver functions:

.. literalinclude:: getting-started/resolvers.py
    :language: python

While we won't go into details concerning the resolvers signature we can already
note that they receive the following parameters:

- The resolved parent value (The server provided root value for top-level fields)
- A context value which is where you provide any application specific data such
  as database connections, loggers, etc. In this case the ``db`` part of the
  context will be a mapping for each entry's id to itself.
- An info object which carries some GraphQL specific data about the current
  execution context.
-  The GraphQL field arguments are passed as keyword parameters.

We haven't implemented any resolver for the field on the ``Character`` type.
That is because the default behavior is to look up field of dictionaries and
objects which is sufficient here.

Refer to :ref:`defining_resolvers` for more details on implementing resolvers.


Executing queries against the schema
------------------------------------

Now that we have a valid schema, we just need to provide client queries for
execution. The execution is carried out by :func:`py_gql.graphql_blocking` (as
all our resolvers are blocking, for different runtimes such as Python's asyncio
we'd use :func:`py_gql.graphql`) and consists of 3 steps:

1. Parsing the client query and validating that it is a correct GraphQL document
2. Validating the query against the schema to verify that it can be executed at all
3. Execute the query and surface any errors or return the data

The return value is an instance of :class:`py_gql.GraphQLResult` which can be
serialized using :meth:`py_gql.GraphQLResult.response`.

We will expose this behind an HTTP API using `Flask <http://flask.pocoo.org/>`_.

.. note::

    While the transport and serialization format depend on the application and
    are technically irrelevant to the GraphQL runtime itself; it is pretty
    common to expose GraphQL APIs behind an HTTP server, traditionally under
    ``POST /graphql`` and JSON encode the request and response which is what
    we're doing  here.

.. literalinclude:: getting-started/flask.py
    :language: python

Pulling together all that we've seen so far you should have a working GraphQL
server that you can test using any HTTP client.

Using `HTTPie <https://httpie.org/>`_ for example (note that the response might
be reordered due to how HTTPie prints json, use ``--pretty=none`` to see the
raw response):

.. literalinclude:: getting-started/queries.txt


Complete code
-------------

.. literalinclude:: ../../examples/getting-started.py
    :linenos:
    :language: python
