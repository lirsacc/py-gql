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

The first step in creating a GraphQL server is defining your the types and
schema that clients will be able to query.

The GraphQL schema that we'll implement for this example is as follow (using
the schema definition language):


.. literalinclude:: getting-started.schema.graphql
   :language: graphql

To define the schema programatically, you use the :mod:`py_gql.schema` module
as follow:

.. literalinclude:: getting-started.schema.py
   :language: python

However this gets pretty verbose and can lead to repetitive boilerplate.
To make things easier you can use :func:`py_gql.schema.build.make_executable_schema`
to generate the schema from the SDL definition:

.. code-block:: python

    from py_gql.schema.build import make_executable_schema
    schema = make_executable_schema("""
        # SDL file content
        ...
    """)


Interacting with your data
--------------------------

The schema as defined above isn't going to be very useful unless we have a way
to interact with our data. By default the runtime looks up fields as dict items and object attributes
of the root value you provide during execution. This works for simple cases, but
it is limited when running dynamic queries (such as fetching an item by id like
in our schema). In order to implement custom field resolution you have to
implement custom field resolvers. This is where your business logic and data
access should live.

For this example we will use the following JSON
dataset:


.. literalinclude:: getting-started.data.json
   :language: json

Let's build a mapping of post id to post and implement our resolver functions:

.. code-block:: python

    import json

    with open('data.json') as df:
        DB = {str(row['id']): row for row in json.loads(DATA)}

    def resolve_post(_, args, context, info):
        # Extract post from DB object
        return context['DB'].get(args['id'])

    def resolve_comments(post, args, context, info):
        # Paginate + add parent post to comment objects to support nesting
        page = post['comments'][args['offset']:args['offset'] + args['count']]
        return [dict(c, post=post) for c in page]


As you can see the resolver function receives 4 arguments:

- The resolved parent value (root value for top-level fields)
- The field arguments
- A context value which is where you provide any application specific value such
  as database connections, loggers, etc.
- An info object which carries some data about the current execution and which we
  will not worry about for this example


The last step is to add these to our schema, we would modify the previous
definition as such:


.. code-block:: python

    ...

    PostType = ObjectType(
        "Post",
        [
            ...,
            Field(
                ...,
                resolve=resolve_comments
            ),
        ],
    )

    ...

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "post",
                    PostType,
                    args=[Argument("id", NonNullType(ID))],
                    resolve=resolve_post,
                )
            ],
        )
    )

And when generating the schema:

.. code-block:: python

    from py_gql.schema.build import make_executable_schema
    schema = make_executable_schema("""
        # SDL file content
        ...
    """, resolvers={
        'Query': {
            'post': resolve_post
        },
        'Post': {
            'comments': resolve_comments,
        }
    })

As you can see, due to the default behaviour described above, we haven't
implemented a resolver for ``Comment->Post`` as ``resolve_comments`` takes care
of adding the ``post`` field to the comment dicts.


Executing queries against the schema
------------------------------------

Now that we have a valid schema, we just need to provide client queries for
execution. The execution is carried out by :func:`py_gql.graphql` and consistst
of 3 steps:

1. Parsing the client query and validating that it is a correct GraphQL document
2. Validating the query against the schema to verifying that it can be executed
   at all
3. Execute the query and surface any errors or return the data

The return value is an instance of :class:`GraphQLResult` which can be
serialized using :meth:`GraphQLResult.response` and :meth:`GraphQLResult.json`.

Here a few examples of queries you can run and their expected result:

.. literalinclude:: getting-started.queries.py
   :language: python


Exposing the schema behind an HTTP endpoint (using Flask)
---------------------------------------------------------

While the transport and serialization format depend on the application and are
technically irrelevant to the GraphQL runtime it is common to expose GraphQL
APIs behind a HTTP server, traditionnaly behind ``POST /graphql`` and JSON
encoded.

For this example we will do so using `Flask <http://flask.pocoo.org/>`_.

.. code-block:: python

    from flask import Flask, Response, request

    app = Flask(__name__)

    @app.route("/graphql", methods=("POST",))
    def graphql_route():
        data = request.json

        result = graphql(
            schema,
            data["query"],
            data.get("variables", {}),
            data.get("operation_name"),
            context=dict(DB=DB)
        )

        return Response(result.json(), mimetype="application/json")

Final code
----------

Pulling together all that we've seen so far you should have a working GraphQL
server that you can test using any HTTP client.

.. literalinclude:: getting-started.full.py
   :language: python

Using `httpie <https://httpie.org/>`_ for example (note that the response will
reordered due to how httpie prints json, use ``--pretty=none`` to see the raw
response)

.. code::

    $ python example.py
    $ http POST :5000/graphql query='... you query here ...'
