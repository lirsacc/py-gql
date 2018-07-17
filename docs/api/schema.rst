Schema Definition
=================

.. module: py_gql.schema

.. automodule:: py_gql.schema

The schema object
-----------------

.. autoclass:: Schema

.. autofunction:: print_schema

Defining Types
--------------

Types are defined as instances of :class:`~py_gql.schema.Type` and its subclasses.

.. autoclass:: Type

.. warning::
    Named types must be unique across a single :class:`~py_gql.schema.Schema`
    instance.

.. note::
    Argument singatures including the `Lazy[]` tag indicate that the value
    can either be of the specified type or a callable returning the specified
    type. For lists it can also be a mixed list of callables and non callables.

    This is here to make supporting definition of cylcic types easier.

    For instance to define the GraphQL type:

    .. code-block:: graphql

        type MyCyclicObject {
            self: MyCyclicObject
        }

    you could interchangeably write:

    .. code-block:: python

        MyCyclicObject = ObjectType('MyCyclicObject', [
            Field('self', lambda: MyCyclicObject)
        ])

    or:

    .. code-block:: python

        MyCyclicObject = ObjectType('MyCyclicObject', [
            lambda: Field('self', MyCyclicObject)
        ])

    or:

    .. code-block:: python

        MyCyclicObject = ObjectType('MyCyclicObject', lambda: [
            Field('self', MyCyclicObject)
        ])


.. autoclass:: WrappingType

.. autoclass:: NonNullType

.. autoclass:: ListType

.. autoclass:: Argument

.. autoclass:: Field

.. autoclass:: ObjectType

.. autoclass:: InterfaceType

.. autoclass:: UnionType

.. autoclass:: EnumValue

.. autoclass:: EnumType

.. autoclass:: ScalarType

.. autoclass:: InputField

.. autoclass:: InputObjectType

.. autoclass:: Directive


.. autofunction:: unwrap_type

.. autofunction:: nullable_type

.. autofunction:: is_input_type

.. autofunction:: is_output_type

.. autofunction:: is_leaf_type

.. autofunction:: is_composite_type

.. autofunction:: is_abstract_type


Scalar Types
------------

Scalar types are instances of :class:`~py_gql.schema.ScalarType`, refer to the
class documentation to learn how to define them.

Specified scalar types
^^^^^^^^^^^^^^^^^^^^^^

The following types are part of the specification and should always be available
in any compliant GraphQL server.

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

Custom scalar types
^^^^^^^^^^^^^^^^^^^

The following types and classes are provided for convenience as they are
quite common. They will not always be present in GraphQL servers.

.. autoattribute:: py_gql.schema.UUID
    :annotation:

    The UUID scalar type represents a UUID as specified in :rfc:`4122`.

.. autoclass:: py_gql.schema.RegexType

Directives
----------

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
