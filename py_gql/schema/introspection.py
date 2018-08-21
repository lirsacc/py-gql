# -*- coding: utf-8 -*-
""" GaphQL types related to introspection queries that
should be present in all spec compliant servers. """
from __future__ import unicode_literals

import json

import six

from .scalars import Boolean, String
from .types import (
    Argument,
    EnumType,
    EnumValue,
    Field,
    InputObjectType,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    UnionType,
    WrappingType,
    is_abstract_type,
)

__Schema__ = ObjectType(
    "__Schema",
    description=(
        "A GraphQL Schema defines the capabilities of a GraphQL server. "
        "It exposes all available types and directives on the server, "
        "as well as the entry points for query, mutation, "
        "and subscription operations."
    ),
    fields=lambda: [
        Field(
            "types",
            NonNullType(ListType(NonNullType(__Type__))),
            description="A list of all types supported by this server.",
            # Sort as the output should not be determined by the way the schema
            # is built and this is the most logical order.
            resolve=lambda schema, *a, **kw: list(
                sorted(schema.types.values(), key=lambda t: t.name)
            ),
        ),
        Field(
            "queryType",
            NonNullType(__Type__),
            description="The type that query operations will be rooted at.",
            resolve=lambda schema, *a, **kw: schema.query_type,
        ),
        Field(
            "mutationType",
            __Type__,
            description=(
                "If this server supports mutation, the type that mutation "
                "operations will be rooted at."
            ),
            resolve=lambda schema, *a, **kw: schema.mutation_type,
        ),
        Field(
            "subscriptionType",
            __Type__,
            description=(
                "If this server supports subscription, the type that "
                "subscription operations will be rooted at."
            ),
            resolve=lambda schema, *a, **kw: schema.subscription_type,
        ),
        Field(
            "directives",
            NonNullType(ListType(NonNullType(__Directive__))),
            description="A list of all directives supported by this server.",
            resolve=lambda schema, *a, **kw: list(
                sorted(schema.directives.values(), key=lambda d: d.name)
            ),
        ),
    ],
)


__Directive__ = ObjectType(
    "__Directive",
    description=(
        "A Directive provides a way to describe alternate runtime execution "
        "and type validation behavior in a GraphQL document."
        "\n\nIn some cases, you need to provide options to alter GraphQL's "
        "execution behavior in ways field arguments will not suffice, such as "
        "conditionally including or skipping a field. Directives provide this "
        "by describing additional information to the executor."
    ),
    fields=lambda: [
        Field("name", NonNullType(String)),
        Field("description", String),
        Field(
            "locations",
            NonNullType(ListType(NonNullType(__DirectiveLocation__))),
        ),
        Field("args", NonNullType(ListType(NonNullType(__InputValue__)))),
    ],
)


__DirectiveLocation__ = EnumType(
    "__DirectiveLocation",
    [
        EnumValue(
            "QUERY", description="Location adjacent to a query operation."
        ),
        EnumValue(
            "MUTATION", description="Location adjacent to a mutation operation."
        ),
        EnumValue(
            "SUBSCRIPTION",
            description="Location adjacent to a subscription operation.",
        ),
        EnumValue("FIELD", description="Location adjacent to a field."),
        EnumValue(
            "FRAGMENT_DEFINITION",
            description="Location adjacent to a fragment definition.",
        ),
        EnumValue(
            "FRAGMENT_SPREAD",
            description="Location adjacent to a fragment spread.",
        ),
        EnumValue(
            "INLINE_FRAGMENT",
            description="Location adjacent to an inline fragment.",
        ),
        EnumValue(
            "SCHEMA", description="Location adjacent to a schema definition."
        ),
        EnumValue(
            "SCALAR", description="Location adjacent to a scalar definition."
        ),
        EnumValue(
            "OBJECT",
            description="Location adjacent to an object type definition.",
        ),
        EnumValue(
            "FIELD_DEFINITION",
            description="Location adjacent to a field definition.",
        ),
        EnumValue(
            "ARGUMENT_DEFINITION",
            description="Location adjacent to an argument definition.",
        ),
        EnumValue(
            "INTERFACE",
            description="Location adjacent to an interface definition.",
        ),
        EnumValue(
            "UNION", description="Location adjacent to a union definition."
        ),
        EnumValue(
            "ENUM", description="Location adjacent to an enum definition."
        ),
        EnumValue(
            "ENUM_VALUE",
            description="Location adjacent to an enum value definition.",
        ),
        EnumValue(
            "INPUT_OBJECT",
            description=(
                "Location adjacent to an input object type definition."
            ),
        ),
        EnumValue(
            "INPUT_FIELD_DEFINITION",
            description=(
                "Location adjacent to an input object field definition."
            ),
        ),
    ],
    description=(
        "A Directive can be adjacent to many parts of the GraphQL language, a "
        "__DirectiveLocation describes one such possible adjacencies."
    ),
)


def _resolve_type_kind(type_, *args, **kwargs):
    if isinstance(type_, ScalarType):
        return "SCALAR"
    elif isinstance(type_, ObjectType):
        return "OBJECT"
    elif isinstance(type_, InterfaceType):
        return "INTERFACE"
    elif isinstance(type_, UnionType):
        return "UNION"
    elif isinstance(type_, EnumType):
        return "ENUM"
    elif isinstance(type_, InputObjectType):
        return "INPUT_OBJECT"
    elif isinstance(type_, ListType):
        return "LIST"
    elif isinstance(type_, NonNullType):
        return "NON_NULL"
    raise TypeError("Unknown kind of type: %s" % type_)


__Type__ = ObjectType(
    "__Type",
    description=(
        "The fundamental unit of any GraphQL Schema is the type. There are "
        "many kinds of types in GraphQL as represented by the `__TypeKind` "
        "enum.\n\nDepending on the kind of a type, certain fields describe "
        "information about that type. Scalar types provide no information "
        "beyond a name and description, while Enum types provide their values. "
        "Object and Interface types provide the fields they describe. Abstract "
        "types, Union and Interface, provide the Object types possible "
        "at runtime. List and NonNull types compose other types."
    ),
    fields=lambda: [
        Field("kind", NonNullType(__TypeKind__), resolve=_resolve_type_kind),
        Field("name", String),
        Field("description", String),
        Field(
            "fields",
            ListType(NonNullType(__Field__)),
            args=[Argument("includeDeprecated", Boolean, default_value=False)],
            resolve=lambda type_, args, *a, **kw: (
                [
                    f
                    for f in type_.fields
                    if (not f.deprecated) or args.get("includeDeprecated")
                ]
                if isinstance(type_, (ObjectType, InterfaceType))
                else None
            ),
        ),
        Field(
            "interfaces",
            ListType(NonNullType(__Type__)),
            resolve=lambda type_, *a, **kw: (
                type_.interfaces if isinstance(type_, ObjectType) else None
            ),
        ),
        Field(
            "possibleTypes",
            ListType(NonNullType(__Type__)),
            resolve=lambda type_, a, c, info: (
                list(
                    sorted(
                        info.schema.get_possible_types(type_),
                        key=lambda t: t.name,
                    )
                )
                if is_abstract_type(type_)
                else None
            ),
        ),
        Field(
            "enumValues",
            ListType(NonNullType(__EnumValue__)),
            args=[Argument("includeDeprecated", Boolean, default_value=False)],
            resolve=lambda type_, args, *a, **kw: (
                [
                    ev
                    for ev in type_.values
                    if (not ev.deprecated) or args.get("includeDeprecated")
                ]
                if isinstance(type_, EnumType)
                else None
            ),
        ),
        Field(
            "inputFields",
            ListType(NonNullType(__InputValue__)),
            resolve=lambda type_, *a, **kw: (
                [f for f in type_.fields]
                if isinstance(type_, InputObjectType)
                else None
            ),
        ),
        Field(
            "ofType",
            __Type__,
            resolve=lambda type_, *a, **kw: (
                type_.type if isinstance(type_, WrappingType) else None
            ),
        ),
    ],
)


__EnumValue__ = ObjectType(
    "__EnumValue",
    description=(
        "One possible value for a given Enum. Enum values are unique values, "
        "not a placeholder for a string or numeric value. However an Enum "
        "value is returned in a JSON response as a string."
    ),
    fields=lambda: [
        Field("name", NonNullType(String)),
        Field("description", String),
        Field(
            "isDeprecated",
            NonNullType(Boolean),
            resolve=lambda ev, *_: ev.deprecated,
        ),
        Field(
            "deprecationReason",
            String,
            resolve=lambda ev, *_: ev.deprecation_reason,
        ),
    ],
)


def _format_default_value(input_value):
    if not input_value.has_default_value:
        return None
    dv = input_value.default_value
    if isinstance(dv, bool):
        return str(dv).lower()
    elif dv is None:
        return "null"
    elif isinstance(dv, six.string_types):
        return '"%s"' % dv
    return json.dumps(dv)


__InputValue__ = ObjectType(
    "__InputValue",
    description=(
        "Arguments provided to Fields or Directives and the input fields "
        "of an InputObject are represented as Input Values which describe "
        "their type and optionally a default value."
    ),
    fields=lambda: [
        Field("name", NonNullType(String)),
        Field("description", String),
        Field("type", NonNullType(__Type__)),
        Field(
            "defaultValue",
            String,
            description=(
                "A GraphQL-formatted string representing the "
                "default value for this input value."
            ),
            resolve=lambda iv, *a, **kw: _format_default_value(iv),
        ),
    ],
)


__Field__ = ObjectType(
    "__Field",
    description=(
        "Object and Interface types are described by a list of Fields, "
        "each of which has a name, potentially a list of arguments, and "
        "a return type."
    ),
    fields=lambda: [
        Field("name", NonNullType(String)),
        Field("description", String),
        Field(
            "args",
            NonNullType(ListType(NonNullType(__InputValue__))),
            resolve=lambda field, *args, **kwargs: (field.args or []),
        ),
        Field("type", NonNullType(__Type__)),
        Field(
            "isDeprecated",
            NonNullType(Boolean),
            resolve=lambda field, *_: field.deprecated,
        ),
        Field(
            "deprecationReason",
            String,
            resolve=lambda field, *_: field.deprecation_reason,
        ),
    ],
)


__TypeKind__ = EnumType(
    "__TypeKind",
    [
        EnumValue("SCALAR", description="Indicates this type is a scalar."),
        EnumValue(
            "OBJECT",
            description=(
                "Indicates this type is an object. `fields` and "
                "`interfaces` are valid fields."
            ),
        ),
        EnumValue(
            "INTERFACE",
            description=(
                "Indicates this type is an interface. `fields` and "
                "`possibleTypes` are valid fields."
            ),
        ),
        EnumValue(
            "UNION",
            description=(
                "Indicates this type is a union. `possibleTypes` is "
                "a valid field."
            ),
        ),
        EnumValue(
            "ENUM",
            description=(
                "Indicates this type is an enum. `enumValues` is a "
                "valid field."
            ),
        ),
        EnumValue(
            "INPUT_OBJECT",
            description=(
                "Indicates this type is an input object. `inputFields` "
                "is a valid field."
            ),
        ),
        EnumValue(
            "LIST",
            description=(
                "Indicates this type is a list. `ofType` is a valid " "field."
            ),
        ),
        EnumValue(
            "NON_NULL",
            description=(
                "Indicates this type is a non-null. `ofType` is a "
                "valid field."
            ),
        ),
    ],
    description="An enum describing what kind of type a given `__Type` is.",
)


INTROPSPECTION_TYPES = (
    __Schema__,
    __Directive__,
    __DirectiveLocation__,
    __Type__,
    __Field__,
    __InputValue__,
    __EnumValue__,
    __TypeKind__,
)

schema_field = Field(
    "__schema",
    NonNullType(__Schema__),
    description="Access the current type schema of this server.",
    args=[],
    resolve=lambda p, a, c, info: info.schema,
)

type_field = Field(
    "__type",
    __Type__,
    description="Request the type information of a single type.",
    args=[Argument("name", NonNullType(String))],
    resolve=lambda p, args, c, info: info.schema.get_type(args["name"], None),
)


type_name_field = Field(
    "__typename",
    NonNullType(String),
    description="The name of the current Object type at runtime.",
    args=[],
    resolve=lambda p, a, c, info: info.parent_type.name,
)


def is_introspection_type(type_):
    return type_ in INTROPSPECTION_TYPES
