# -*- coding: utf-8 -*-

import pytest

from py_gql import build_schema, graphql_blocking

SDL = """
type Query {
    foo: String,
    bar: String
}
"""


def test_register_resolver():
    schema = build_schema(SDL)
    schema.register_resolver("Query", "foo", lambda *_: "foo")
    assert (
        "foo" == graphql_blocking(schema, "{ foo }").response()["data"]["foo"]
    )


def test_resolver_decorator():
    schema = build_schema(SDL)

    @schema.resolver("Query.foo")
    def _resolve_foo(*_):
        return "foo"

    assert (
        "foo" == graphql_blocking(schema, "{ foo }").response()["data"]["foo"]
    )


def test_resolver_decorator_multiple_applications():
    schema = build_schema(SDL)

    @schema.resolver("Query.bar")
    @schema.resolver("Query.foo")
    def _resolve_foo(*_):
        return "foo"

    assert {"foo": "foo", "bar": "foo"} == graphql_blocking(
        schema, "{ foo, bar }"
    ).response()["data"]


def test_resolver_decorator_invalid_path():
    schema = build_schema(SDL)

    with pytest.raises(ValueError):
        schema.resolver("Query")(lambda *_: "foo")
