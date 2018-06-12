# -*- coding: utf-8 -*-
"""
GraphQL is a data query language developed by Facebook intended to
serve mobile and web application frontends.

This is a simple GraphQL library for Python meant to be used on its own
to build GraphQL servers. It supports:

- Parsing the GraphQL language (Query language and SDL).
- Building a GraphQL type schema.
- Validating a GraphQL request against a type schema.
- Executing a GraphQL request against a type schema.
"""

# flake8: noqa

from ._graphql import graphql, GraphQLResult
from .schema import (
    Schema,
    ObjectType,
    Arg,
    Directive,
    Argument,
    EnumValue,
    EnumType,
    Field,
    ObjectType,
    InputField,
    InputObjectType,
    InterfaceType,
    ListType,
    NonNullType,
    ScalarType,
    UnionType,
    Int,
    String,
    Int,
    Float,
    ID,
    UUID,
    String,
    Boolean,
    RegexType,
)
