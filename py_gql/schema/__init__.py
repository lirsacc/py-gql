# -*- coding: utf-8 -*-
""" Programatically creating, validating and inspecting GraphQL schemas.

This module directly exposes all the necessary objects to build a valid
GraphQL schema against which to execute queries.

Schema
------

.. autoclass:: Schema
    :show-inheritance:

.. autofunction:: print_schema

Defining Types
--------------

Types are defined as instances of :class:`~py_gql.schema.Type` and
:class:`~py_gql.schema.NamedType` and their subclasses.

.. autoclass:: Type
    :show-inheritance:

.. autoclass:: NamedType
    :show-inheritance:

Warning:
    Named types must be unique across a single :class:`~py_gql.schema.Schema`
    instance.

Note:
    Argument singatures including the `Lazy[]` tag indicate that the value
    can either be of the specified type or a callable returning the specified
    type. For lists it can also be a list of callables and non callables.

    This is here to make supporting definition of cylcic types easier.

    For instance to define the GraphQL type:

    .. code-block:: graphql

        type MyCyclicObject {
            self: MyCyclicObject
        }

    you could write:

    .. code-block:: python

        MyCyclicObject = ObjectType('MyCyclicObject', [
            Field('self', lambda: MyCyclicObject)
        ])

    or:

    .. code-block:: python

        MyCyclicObject = ObjectType('MyCyclicObject', [
            lambda: Field('self', MyCyclicObject)
        ])


.. autoclass:: WrappingType
    :show-inheritance:
.. autoclass:: NonNullType
    :show-inheritance:
.. autoclass:: ListType
    :show-inheritance:
.. autoclass:: Argument
    :show-inheritance:
.. autoclass:: Field
    :show-inheritance:
.. autoclass:: ObjectType
    :show-inheritance:
.. autoclass:: InterfaceType
    :show-inheritance:
.. autoclass:: UnionType
    :show-inheritance:
.. autoclass:: EnumValue
    :show-inheritance:
.. autoclass:: EnumType
    :show-inheritance:
.. autoclass:: ScalarType
    :show-inheritance:
.. autoclass:: InputField
    :show-inheritance:
.. autoclass:: InputObjectType
    :show-inheritance:
.. autoclass:: Directive
    :show-inheritance:

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

The following are part of the specification and should always be available
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

The following types and classes are provided as a convenience as they are
quite common. They will not always be present in GraphQL server.

.. autoattribute:: py_gql.schema.UUID
    :annotation:

    The UUID scalar type represents a UUID as specified in :rfc:`4122`.

.. autoclass:: py_gql.schema.RegexType

Directives
----------

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

"""

# flake8: noqa

from .types import (
    Argument,
    Directive,
    EnumValue,
    EnumType,
    Field,
    ObjectType,
    InputField,
    InputObjectType,
    InterfaceType,
    is_abstract_type,
    is_composite_type,
    is_input_type,
    is_leaf_type,
    is_output_type,
    ListType,
    NonNullType,
    nullable_type,
    ScalarType,
    Type,
    UnionType,
    unwrap_type,
    NamedType,
    WrappingType,
)
from .scalars import Int, Float, ID, UUID, String, Boolean, RegexType
from .directives import IncludeDirective, SkipDirective, DeprecatedDirective
from .schema import Schema
from .printer import print_schema
from ._schema_from_ast import schema_from_ast
