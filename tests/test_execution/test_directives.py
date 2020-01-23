# -*- coding: utf-8 -*-
""" execution tests related to directive handling """

import pytest

from py_gql.execution import execute
from py_gql.lang import parse
from py_gql.schema import (
    Argument,
    Directive,
    Field,
    Int,
    ObjectType,
    Schema,
    String,
)

from ._test_utils import assert_sync_execution

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

test_type = ObjectType("TestType", [Field("a", String), Field("b", String)])
schema = Schema(test_type)
root = {"a": lambda *_: "a", "b": lambda *_: "b"}


async def test_without_directives():
    assert_sync_execution(
        schema,
        "{ a, b }",
        initial_value=root,
        expected_data={"a": "a", "b": "b"},
    )


@pytest.mark.parametrize(
    "directive,value,expected",
    [
        ("include", "true", {"a": "a", "b": "b"}),
        ("include", "false", {"b": "b"}),
        ("skip", "true", {"b": "b"}),
        ("skip", "false", {"a": "a", "b": "b"}),
    ],
)
async def test_built_ins_on_scalars(directive, value, expected):
    query = "{ a @%s(if: %s), b }" % (directive, value)
    assert_sync_execution(
        schema, query, initial_value=root, expected_data=expected
    )


@pytest.mark.parametrize(
    "directive,value,expected",
    [
        ("include", "true", {"a": "a", "b": "b"}),
        ("include", "false", {}),
        ("skip", "true", {}),
        ("skip", "false", {"a": "a", "b": "b"}),
    ],
)
async def test_built_ins_on_fragment_spreads(directive, value, expected):
    query = """
    { ...f @%s(if: %s) }
    fragment f on TestType { a, b }
    """ % (
        directive,
        value,
    )
    assert_sync_execution(
        schema, query, initial_value=root, expected_data=expected
    )


@pytest.mark.parametrize(
    "directive,value,expected",
    [
        ("include", "true", {"a": "a", "b": "b"}),
        ("include", "false", {"b": "b"}),
        ("skip", "true", {"b": "b"}),
        ("skip", "false", {"a": "a", "b": "b"}),
    ],
)
async def test_built_ins_on_inline_fragments(directive, value, expected):
    query = """{
        b
        ... on TestType @%s(if: %s) { a }
    }""" % (
        directive,
        value,
    )
    assert_sync_execution(
        schema, query, initial_value=root, expected_data=expected
    )


@pytest.mark.parametrize(
    "directive,value,expected",
    [
        ("include", "true", {"a": "a", "b": "b"}),
        ("include", "false", {"b": "b"}),
        ("skip", "true", {"b": "b"}),
        ("skip", "false", {"a": "a", "b": "b"}),
    ],
)
async def test_built_ins_on_anonymous_inline_fragments(
    directive, value, expected
):
    query = """{
        b
        ... @%s(if: %s) { a }
    }""" % (
        directive,
        value,
    )
    assert_sync_execution(
        schema, query, initial_value=root, expected_data=expected
    )


@pytest.mark.parametrize(
    "include,skip,expected",
    [
        ("true", "false", {"a": "a", "b": "b"}),
        ("true", "true", {"b": "b"}),
        ("false", "true", {"b": "b"}),
        ("false", "false", {"b": "b"}),
    ],
)
async def test_include_and_skip(include, skip, expected):
    query = "{ a @include(if: %s) @skip(if: %s), b }" % (include, skip)
    assert_sync_execution(
        schema, query, initial_value=root, expected_data=expected
    )


async def test_get_directive_arguments_known(mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    execute(
        Schema(test_type, directives=[CustomDirective]),
        parse('{ a @custom(a: "foo", b: 42) }'),
        initial_value={"a": resolver},
    )

    (_, info), _ = resolver.call_args

    assert info.get_directive_arguments("custom") == {
        "a": "foo",
        "b": 42,
    }


async def test_get_directive_arguments_known_with_variables(mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    execute(
        Schema(test_type, directives=[CustomDirective]),
        parse('query ($b: Int!) { a @custom(a: "foo", b: $b) }'),
        initial_value={"a": resolver},
        variables={"b": 42},
    )

    (_, info), _ = resolver.call_args

    assert info.get_directive_arguments("custom") == {
        "a": "foo",
        "b": 42,
    }


async def test_get_directive_arguments_missing(mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    execute(
        Schema(test_type, directives=[CustomDirective]),
        parse("{ a }"),
        initial_value={"a": resolver},
    )

    (_, info), _ = resolver.call_args

    assert info.get_directive_arguments("custom") is None


async def test_get_directive_arguments_unknown(mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    execute(
        Schema(test_type, directives=[CustomDirective]),
        parse('{ a @custom(a: "foo", b: 42) }'),
        initial_value={"a": resolver},
    )

    (_, info), _ = resolver.call_args

    with pytest.raises(KeyError):
        info.get_directive_arguments("foo")
