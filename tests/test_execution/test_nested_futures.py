# -*- coding: utf-8 -*-
""" Ensure resolvers can return futures by tagging on the current executor
"""

from py_gql.execution import execute
from py_gql.execution.executors import ThreadPoolExecutor
from py_gql.lang import parse
from py_gql.schema import Field, Int, ObjectType, Schema


def test_execute_awaits_nested_future():
    def resolver(root, args, context, info):
        return info.executor.submit(lambda *a, **kw: 42)

    schema = Schema(ObjectType("Query", [Field("foo", Int, resolve=resolver)]))

    with ThreadPoolExecutor() as executor:
        data, errors = execute(schema, parse("{ foo }"), executor=executor)

    assert data == {"foo": 42}
    assert errors == []


def test_execute_awaits_deeply_nested_future():
    def deep_resolver(root, args, context, info):
        return info.executor.submit(lambda *a, **kw: 42)

    def resolver(root, args, context, info):
        return lambda: info.executor.submit(deep_resolver, root, args, context, info)

    schema = Schema(ObjectType("Query", [Field("foo", Int, resolve=resolver)]))

    with ThreadPoolExecutor() as executor:
        data, errors = execute(schema, parse("{ foo }"), executor=executor)

    assert data == {"foo": 42}
    assert errors == []
