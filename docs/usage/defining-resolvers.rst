.. _defining_resolvers:

Defining resolvers
==================

In a GraphQL server, resolvers describe the logic that;s executed to fetches
fetch specific fields. It's where your application code for data access and
business logic usually hooks into the GraphQL schema.


Resolver signature
------------------

Resolvers should roughly match a signature similar to this:

.. code-block:: python

    def resolver(root, context, info, **arguments):
            ...

Every resolvers is expected to accept 3 positional parameters and keyword
parameters:

- ``root``: the current parent value
    - The server provided root value for top-level fields (`Query`, `Mutation`)
    - The parent value of the object whose field is being resolver
- ``ctx``: the application provided context value. This is where application
  specific data such as database connections, loggers, etc. should be provided.
- ``info``: A :class:`~py_gql.execution.ResolveInfo` object which carries GraphQL
  specific information about the field being currently resolved. This should be
  rarely used by most people outside of custom directives handling and query
  optimizations such as collapsing requests or join optimisation.
- The GraphQL field arguments are passed as keyword parameters. Required
  arguments and arguments with default values will always be passed in while
  optional arguments with no default will be omitted when not present in the
  query.

py-gql will attempt to validate the expected parameters of resolvers when
validating a schema using :meth:`~py_gql.schema.Schema.validate`. This is
however best effort and doesn't always work, for instance C-Extension defined
function cannot always be inspected with :py:func:`inspect.signature`.


Adding resolvers to the schema
------------------------------

As there are multiple ways to define schema, there are multiple ways to attach
resolvers.

Resolvers can be attached through the :class:`~py_gql.schema.Schema` object:

.. code-block:: python

    schema = build_schema(...)

    @schema.resolver("Query.characters")
    def resolve_characters(root, ctx, info):
        return ctx.api.fetch_characters()

    def resolve_character_friends(character, ctx, info, limit=10):
        return ctx.api.fetch_friends(character, limit=limit)

    schema.register_resolver("Character", "friends", resolve_character_friends)


In case the schema is built without using `build_schema`, the resolvers can be
added directly to :class:`~py_gql.schema.Field` objects:

.. code-block:: python

    def resolve_character_friends(character, ctx, info, limit=10):
        return ctx.api.fetch_friends(character, limit=limit)

    Character = ObjectType("Character", [
        ...
        Field(
            "friends",
            lambda: Character.as_list(),
            [
                Argument("limit", Int.as_non_null(), default_value=10),
            ],
            resolver=resolve_character_friends,
        )
        ...
    ])


Default resolver
----------------

It is not necessary to specify resolvers for every type in the schema. By
default a default resolver implementation is used if no custom resolver has
been defined for a given field. It should cover the majority of simple cases by
extracting values from their parent by:

- Doing a key lookup if the parent is a :py:class:`collections.abc.Mapping`.
- Returning the parent's attribute if present.
- Calling the parent's method if present, passing in all resolver arguments
  except the root object.

See :func:`py_gql.execution.default_resolver` for the exact implementation.


Overriding the default resolver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are cases where defining resolver per field could be overkill and you
instead want to define catch-all resolver globally or per object type, or simply
there is better implementation of the default resolver for your use case. This
can be done at 2 levels of override.

You can override the default resolver at the schema level:

.. code-block:: python

    schema = build_schema(...)

    def default_resolver(root, ctx, info, **args):
        return getattr(root, info.field_definition.python_name)

    schema.default_resolver = default_resolver

You can also override the default resolver at the object level:

.. code-block:: python

    schema = build_schema(...)

    @schema.resolver("Foo.*")
    def default_resolver(root, ctx, info, **args):
        return getattr(root, info.field_definition.python_name)

    # or
    schema.register_default_resolver("Bar", default_resolver)

    # or, assuming Baz is an ObjectType
    schema.types["Baz"].default_resolver = default_resolver
