# -*- coding: utf-8 -*-

import pytest

from py_gql._string_utils import dedent
from py_gql.exc import ResolverError
from py_gql.execution import GraphQLExtension, GraphQLResult


def test_GraphQLResult_response_with_nothing():
    assert GraphQLResult().response() == {}


def test_GraphQLResult_json():
    assert GraphQLResult(data={"foo": 42}).json(indent=4) == dedent(
        """
        {
            "data": {
                "foo": 42
            }
        }"""
    )


def test_GraphQLResult_bool():
    assert GraphQLResult(data={"foo": 42})
    assert not GraphQLResult(errors=[ResolverError("foo")])
    assert not GraphQLResult(data={"foo": None}, errors=[ResolverError("foo")])


def test_GraphQLResult_add_extension():
    class Ext(GraphQLExtension):
        @property
        def name(self):
            return "foo"

        def payload(self):
            return {"bar": "baz"}

    r = GraphQLResult()
    r.add_extension(Ext())
    assert r.response() == {"extensions": {"foo": {"bar": "baz"}}}


def test_GraphQLResult_add_extension_raises_on_duplicate():
    class Ext(GraphQLExtension):
        name = "foo"

        def payload(self):
            return {"bar": "baz"}

    r = GraphQLResult()
    r.add_extension(Ext())
    with pytest.raises(ValueError) as exc_info:
        r.add_extension(Ext())

    assert str(exc_info.value) == 'Duplicate extension "foo"'
