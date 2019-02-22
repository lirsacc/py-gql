# -*- coding: utf-8 -*-

from typing import List

import pytest

from py_gql.exc import CoercionError
from py_gql.lang import ast as _ast
from py_gql.schema import Argument, Field, Int, NonNullType
from py_gql.utilities import coerce_argument_values


def _test_node(argument_value=None):
    if argument_value is None:
        arguments = []  # type: List[_ast.Argument]
    else:
        arguments = [
            _ast.Argument(name=_ast.Name(value="foo"), value=argument_value)
        ]
    return _ast.Field(name=_ast.Name(value="test"), arguments=arguments)


def _var(name):
    return _ast.Variable(name=_ast.Name(value=name))


def test_missing_nullable_arg_with_default():
    arg = Argument("foo", Int, default_value=42)
    field = Field("test", Int, [arg])
    node = _test_node()
    assert coerce_argument_values(field, node) == {"foo": 42}


def test_missing_nullable_arg_without_default():
    arg = Argument("foo", Int)
    field = Field("test", Int, [arg])
    node = _test_node()
    assert coerce_argument_values(field, node) == {}


def test_missing_non_nullable_arg_with_default():
    arg = Argument("foo", NonNullType(Int), default_value=42)
    field = Field("test", Int, [arg])
    node = _test_node()
    assert coerce_argument_values(field, node) == {"foo": 42}


def test_missing_non_nullable_arg_without_default():
    arg = Argument("foo", NonNullType(Int))
    field = Field("test", Int, [arg])
    node = _test_node()
    with pytest.raises(CoercionError) as exc_info:
        coerce_argument_values(field, node)
    assert (
        str(exc_info.value)
        == 'Argument "foo" of required type "Int!" was not provided'
    )


def test_provided_value():
    arg = Argument("foo", Int)
    field = Field("test", Int, [arg])
    node = _test_node(_ast.IntValue(value="42"))
    assert coerce_argument_values(field, node) == {"foo": 42}


def test_provided_invalid_value():
    arg = Argument("foo", Int)
    field = Field("test", Int, [arg])
    node = _test_node(_ast.StringValue(value="foo"))
    with pytest.raises(CoercionError) as exc_info:
        assert coerce_argument_values(field, node)
    assert str(exc_info.value) == (
        'Argument "foo" of type "Int" was provided invalid value "foo" '
        "(Invalid literal StringValue)"
    )


def test_provided_known_variable():
    arg = Argument("foo", Int)
    field = Field("test", Int, [arg])
    node = _test_node(_var("bar"))
    assert coerce_argument_values(field, node, {"bar": 42}) == {"foo": 42}


def test_provided_unknown_variable_without_default_nullable():
    arg = Argument("foo", Int)
    field = Field("test", Int, [arg])
    node = _test_node(_var("bar"))
    assert coerce_argument_values(field, node) == {}


def test_provided_unknown_variable_without_default_non_nullable():
    arg = Argument("foo", NonNullType(Int))
    field = Field("test", Int, [arg])
    node = _test_node(_var("bar"))
    with pytest.raises(CoercionError) as exc_info:
        coerce_argument_values(field, node)
    assert str(exc_info.value) == (
        'Argument "foo" of required type "Int!" was provided the missing '
        'variable "$bar"'
    )
