# -*- coding: utf-8 -*-

import pytest

from py_gql.exc import CoercionError
from py_gql.lang import parse
from py_gql.schema import Argument, Directive, IncludeDirective, Int, String
from py_gql.utilities import directive_arguments

CustomDirective = Directive(
    "custom", ["FIELD"], [Argument("a", String), Argument("b", Int)]
)


def test_include():
    doc = parse("{ a @include(if: true) }")
    assert directive_arguments(
        IncludeDirective,
        doc.definitions[0].selection_set.selections[0],  # type: ignore
        {},
    ) == {"if": True}


def test_include_missing():
    doc = parse("{ a @include(a: 42) }")
    with pytest.raises(CoercionError):
        directive_arguments(
            IncludeDirective,
            doc.definitions[0].selection_set.selections[0],  # type: ignore
            {},
        )


def test_include_extra():
    doc = parse("{ a @include(a: 42, if: true) }")
    assert directive_arguments(
        IncludeDirective,
        doc.definitions[0].selection_set.selections[0],  # type: ignore
        {},
    ) == {"if": True}


def test_custom_directive_field():
    doc = parse('{ a @custom(a: "foo", b: 42) }')
    assert directive_arguments(
        CustomDirective,
        doc.definitions[0].selection_set.selections[0],  # type: ignore
        {},
    ) == {"a": "foo", "b": 42}


def test_custom_directive_field_variables():
    doc = parse('{ a @custom(a: "foo", b: $b) }')
    assert directive_arguments(
        CustomDirective,
        doc.definitions[0].selection_set.selections[0],  # type: ignore
        {"b": 42},
    ) == {"a": "foo", "b": 42}
