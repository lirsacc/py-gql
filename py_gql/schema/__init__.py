# -*- coding: utf-8 -*-
"""
The :mod:`py_gql.schema` module exposes all the necessary classes and
functions to programatically creating, validating and inspecting GraphQL
schemas against which you can execute queries.
"""

# TODO: Encode as much of the rules a validate_schema in the type system

# isort:skip_file
# flake8: noqa

from .types import (
    AbstractTypes,
    Argument,
    CompositeTypes,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputField,
    InputObjectType,
    InterfaceType,
    is_abstract_type,
    is_composite_type,
    is_input_type,
    is_leaf_type,
    is_output_type,
    LeafTypes,
    ListType,
    NonNullType,
    nullable_type,
    ObjectType,
    OutputTypes,
    ScalarType,
    Type,
    UnionType,
    unwrap_type,
)
from .scalars import (
    Int,
    Float,
    ID,
    UUID,
    String,
    Boolean,
    RegexType,
    SPECIFIED_SCALAR_TYPES,
)
from .directives import (
    IncludeDirective,
    SkipDirective,
    DeprecatedDirective,
    SPECIFIED_DIRECTIVES,
)

from .schema_from_ast import (
    build_schema,
    build_schema_ignoring_extensions,
    extend_schema,
)
from .schema_directives import (
    apply_schema_directives,
    SchemaDirective,
    DeprecatedSchemaDirective,
)
from .schema_visitor import SchemaVisitor
from .schema import Schema
