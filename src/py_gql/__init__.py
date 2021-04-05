# -*- coding: utf-8 -*-
"""
py_gql

py_gql is a pure python implementation of the `GraphQL <https://graphql.org/>`_
query language for Python 3.6+.

The main :mod:`py_gql` package provides the minimum required to build GraphQL
schemas and execute queries against them while the relevant submodules allow
you implement custom behaviors and runtimes.
"""

from .version import __version__  # isort:skip

from . import lang, schema, tracers, utilities  # noqa: F401
from ._graphql import graphql, graphql_blocking, process_graphql_query
from .execution import GraphQLResult, ResolveInfo
from .sdl import build_schema


__all__ = (
    "__version__",
    "graphql",
    "graphql_blocking",
    "process_graphql_query",
    "GraphQLResult",
    "ResolveInfo",
    "build_schema",
)
