Defining GraphQL Schemas
========================

.. module: py_gql.schema

.. automodule:: py_gql.schema

The schema class
----------------

.. autoclass:: Schema
    :members:

Defining Types
--------------

Types are defined as instances of :class:`~py_gql.schema.GraphQLType` and its
subclasses.

.. autoclass:: GraphQLType

.. autoclass:: NamedType
    :members:

.. autoclass:: NonNullType
    :members:

.. autoclass:: ListType
    :members:

.. autoclass:: Argument
    :members:

.. autoclass:: Field
    :members:

.. autoclass:: ObjectType
    :members:

.. autoclass:: InterfaceType
    :members:

.. autoclass:: UnionType
    :members:

.. autoclass:: InputField
    :members:

.. autoclass:: InputObjectType
    :members:

.. autoclass:: EnumValue
    :members:

.. autoclass:: EnumType
    :members:

Scalar Types
~~~~~~~~~~~~

.. autoclass:: ScalarType
    :members:

Specified scalar types
^^^^^^^^^^^^^^^^^^^^^^

The following types are part of the specification and should always be available
in any compliant GraphQL server (although they may not be used).

.. autoattribute:: py_gql.schema.Boolean
    :annotation:

    The `Boolean` scalar type represents ``true`` or ``false``.

.. autoattribute:: py_gql.schema.Int
    :annotation:

    The Int scalar type represents non-fractional signed whole numeric values.
    Int can represent values between -(2^31) and 2^31 - 1.

.. autoattribute:: py_gql.schema.Float
    :annotation:

    The Float scalar type represents signed double-precision fractional values as
    specified by `IEEE 754 <http://en.wikipedia.org/wiki/IEEE_floating_point>`_.

.. autoattribute:: py_gql.schema.String
    :annotation:

    The String scalar type represents textual data, represented as UTF-8
    character sequences. The String type is most often used by GraphQL to
    represent free-form human-readable text.

.. autoattribute:: py_gql.schema.ID
    :annotation:

    The ID scalar type represents a unique identifier, often used to
    refetch an object or as key for a cache. The ID type appears in a
    JSON response as a String; however, it is not intended to be
    human-readable. When expected as an input type, any string (such
    as `"4"`) or integer (such as `4`) input value will be accepted as
    an ID.

.. autoattribute:: py_gql.schema.SPECIFIED_SCALAR_TYPES
    :annotation:

    Tuple of all specified scalar types.

Extra scalar types
^^^^^^^^^^^^^^^^^^

The following types and classes are provided for convenience as they are
quite common. They will not always be present in GraphQL servers and need to be
included manually when using `py_gql.build_schema`.

.. autoattribute:: py_gql.schema.UUID
    :annotation:

    The UUID scalar type represents a UUID as specified in :rfc:`4122`.

.. autoclass:: RegexType
    :members:

Directives
~~~~~~~~~~

.. autoclass:: Directive
    :members:

The following :class:`py_gql.schema.Directive` instances are part of
the specification and should always be available in any compliant GraphQL
server.

.. autoattribute:: py_gql.schema.IncludeDirective
    :annotation:

    Directs the server to include this field or fragment only when
    the ``if`` argument is true.

.. autoattribute:: py_gql.schema.SkipDirective
    :annotation:

    Directs the server to skip this field or fragment when the ``if``
    argument is true.

.. autoattribute:: py_gql.schema.DeprecatedDirective
    :annotation:

    Explains why this element was deprecated, usually also
    including a suggestion for how to access supported
    similar data.
    Formatted in `Markdown <https://daringfireball.net/projects/markdown/>`_.

.. autoattribute:: py_gql.schema.SPECIFIED_DIRECTIVES
    :annotation:

    Tuple of all specified directives.
