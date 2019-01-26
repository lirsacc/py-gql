# -*- coding: utf-8 -*-
""" This module exposes all necessary utilities to execute graphql queries
"""

# flake8: noqa

from . import lang, schema, utilities
from ._graphql import graphql, graphql_sync
from .execution import GraphQLExtension, GraphQLResult, ResolveInfo

__all__ = ("graphql", "GraphQLResult", "GraphQLExtension", "ResolveInfo")
