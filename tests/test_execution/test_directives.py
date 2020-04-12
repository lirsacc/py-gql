# -*- coding: utf-8 -*-
"""
Execution tests related to directive handling.
"""

import pytest

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


class _obj:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

test_type = ObjectType("TestType", [Field("a", String), Field("b", String)])
schema = Schema(test_type)
root = _obj(a=lambda *_: "a", b=lambda *_: "b")


async def test_without_directives(assert_execution):
    await assert_execution(
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
async def test_built_ins_on_scalars(
    assert_execution, directive, value, expected
):
    query = "{ a @%s(if: %s), b }" % (directive, value)
    await assert_execution(
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
async def test_built_ins_on_fragment_spreads(
    assert_execution, directive, value, expected
):
    query = """
    { ...f @%s(if: %s) }
    fragment f on TestType { a, b }
    """ % (
        directive,
        value,
    )
    await assert_execution(
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
async def test_built_ins_on_inline_fragments(
    assert_execution, directive, value, expected
):
    query = """{
        b
        ... on TestType @%s(if: %s) { a }
    }""" % (
        directive,
        value,
    )
    await assert_execution(
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
    assert_execution, directive, value, expected
):
    query = """{
        b
        ... @%s(if: %s) { a }
    }""" % (
        directive,
        value,
    )
    await assert_execution(
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
async def test_include_and_skip(assert_execution, include, skip, expected):
    query = "{ a @include(if: %s) @skip(if: %s), b }" % (include, skip)
    await assert_execution(
        schema, query, initial_value=root, expected_data=expected
    )


async def test_get_directive_arguments_known(assert_execution, mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    await assert_execution(
        Schema(test_type, directives=[CustomDirective]),
        parse('{ a @custom(a: "foo", b: 42) }'),
        initial_value=_obj(a=resolver),
        expected_data={"a": "42"},
    )

    (_, info), _ = resolver.call_args

    assert info.get_directive_arguments("custom") == {
        "a": "foo",
        "b": 42,
    }


async def test_get_directive_arguments_known_with_variables(
    assert_execution, mocker
):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    await assert_execution(
        Schema(test_type, directives=[CustomDirective]),
        parse('query ($b: Int!) { a @custom(a: "foo", b: $b) }'),
        initial_value=_obj(a=resolver),
        variables={"b": 42},
        expected_data={"a": "42"},
    )

    (_, info), _ = resolver.call_args

    assert info.get_directive_arguments("custom") == {
        "a": "foo",
        "b": 42,
    }


async def test_get_directive_arguments_missing(assert_execution, mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    await assert_execution(
        Schema(test_type, directives=[CustomDirective]),
        parse("{ a }"),
        initial_value=_obj(a=resolver),
        expected_data={"a": "42"},
    )

    (_, info), _ = resolver.call_args

    assert info.get_directive_arguments("custom") is None


async def test_get_directive_arguments_unknown(assert_execution, mocker):
    CustomDirective = Directive(
        "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
    )

    resolver = mocker.Mock(return_value=42)

    await assert_execution(
        Schema(test_type, directives=[CustomDirective]),
        parse('{ a @custom(a: "foo", b: 42) }'),
        initial_value=_obj(a=resolver),
        expected_data={"a": "42"},
    )

    (_, info), _ = resolver.call_args

    with pytest.raises(KeyError):
        info.get_directive_arguments("foo")
