# -*- coding: utf-8 -*-
"""
py_gql
~~~~~~

py_gql is a pure python implementation of the `GraphQL <https://graphql.org/>`_
query language for Python 3.5+.

The main :mod:`py_gql` package provides the minimum required to build GraphQL
schemas and execute queries against them while the relevant submodules allow
you to customize the library's behaviour or implement your own GraphQL layer
on top of :mod:`py_gql`.
"""

# flake8: noqa

from . import lang, schema, utilities
from ._graphql import graphql, graphql_blocking
from .execution import GraphQLExtension, GraphQLResult, ResolveInfo
from .schema import build_schema

__all__ = (
    "graphql",
    "graphql_blocking",
    "GraphQLResult",
    "GraphQLExtension",
    "ResolveInfo",
    "build_schema",
)
