# -*- coding: utf-8 -*-

from typing import Any

import pytest

from py_gql.lang import ast as _ast
from py_gql.schema import (
    ID,
    Boolean,
    EnumType,
    Field,
    Float,
    InputField,
    InputObjectType,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    String,
)
from py_gql.schema.scalars import MAX_INT
from py_gql.utilities import ast_node_from_value


def _custom_serialize(x: Any) -> Any:
    if x == 42:
        return None
    return x


class _Object:
    def __repr__(self):
        return "<OBJECT>"


CustomScalar = ScalarType(
    name="CustomScalar", serialize=_custom_serialize, parse=lambda x: x
)  # type: ScalarType


def test_raises_on_non_input_type():
    with pytest.raises(TypeError):
        ast_node_from_value(42, ObjectType("Foo", [Field("foo", Int)]))


@pytest.mark.parametrize(
    "value, input_type, expected",
    [
        (True, Boolean, _ast.BooleanValue(value=True)),
        (False, Boolean, _ast.BooleanValue(value=False)),
        (None, Boolean, _ast.NullValue()),
        (1, Boolean, _ast.BooleanValue(value=True)),
        (0, Boolean, _ast.BooleanValue(value=False)),
        (0, NonNullType(Boolean), _ast.BooleanValue(value=False)),
        (
            None,
            NonNullType(Boolean),
            ValueError('Value of type "Boolean!" cannot be null'),
        ),
        (-1, Int, _ast.IntValue(value="-1")),
        (123.0, Int, _ast.IntValue(value="123")),
        (1e4, Int, _ast.IntValue(value="10000")),
        (
            123.5,
            Int,
            ValueError("Int cannot represent non integer value: 123.5"),
        ),
        (
            1e40,
            Int,
            ValueError("Int cannot represent non 32-bit signed integer: 1e+40"),
        ),
        (-1, Float, _ast.IntValue(value="-1")),
        (123.0, Float, _ast.IntValue(value="123")),
        (123.5, Float, _ast.FloatValue(value="123.5")),
        (1e4, Float, _ast.IntValue(value="10000")),
        (1e40, Float, _ast.FloatValue(value="1e+40")),
        ("hello", String, _ast.StringValue(value="hello")),
        ("VALUE", String, _ast.StringValue(value="VALUE")),
        ("VA\nLUE", String, _ast.StringValue(value="VA\nLUE")),
        (123, String, _ast.StringValue(value="123")),
        (False, String, _ast.StringValue(value="false")),
        (None, String, _ast.NullValue()),
        ("hello", ID, _ast.StringValue(value="hello")),
        (-1, ID, _ast.IntValue(value="-1")),
        (123, ID, _ast.IntValue(value="123")),
        ("01", ID, _ast.StringValue(value="01")),
        (None, ID, _ast.NullValue()),
        (42, CustomScalar, _ast.NullValue()),
        ("42.42", CustomScalar, _ast.FloatValue(value="42.42")),
        (42.42, CustomScalar, _ast.FloatValue(value="42.42")),
        (MAX_INT + 2, CustomScalar, _ast.FloatValue(value="2147483649")),
        ("foo", CustomScalar, _ast.StringValue(value="foo")),
        # - MAX_INT + 1
        ("2147483648", CustomScalar, _ast.FloatValue(value="2147483648")),
        ("2147483648", Float, _ast.FloatValue(value="2147483648.0")),
        (
            _Object(),
            CustomScalar,
            ValueError('Cannot convert value <OBJECT> for type "CustomScalar"'),
        ),
    ],
)
def test_ast_node_from_value_with_scalars(value, input_type, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected)) as exc_info:
            ast_node_from_value(value, input_type)
        assert str(expected) == str(exc_info.value)
    else:
        assert ast_node_from_value(value, input_type) == expected


# Must still be hashable to work with enums
complex_value = ("someArbitrary", "complexValue")

Enum = EnumType("MyEnum", ["HELLO", "GOODBYE", ("COMPLEX", complex_value)])


@pytest.mark.parametrize(
    "value, expected",
    [
        ("HELLO", _ast.EnumValue(value="HELLO")),
        ("GOODBYE", _ast.EnumValue(value="GOODBYE")),
        (complex_value, _ast.EnumValue(value="COMPLEX")),
        ("hello", ValueError("Invalid value 'hello' for enum MyEnum")),
        ("VALUE", ValueError("Invalid value 'VALUE' for enum MyEnum")),
    ],
)
def test_ast_node_from_value_with_enums(value, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected)) as exc_info:
            ast_node_from_value(value, Enum)
        assert str(expected) == str(exc_info.value)
    else:
        assert ast_node_from_value(value, Enum) == expected


@pytest.mark.parametrize(
    "value, input_type, expected",
    [
        (
            ["FOO", "BAR"],
            ListType(String),
            _ast.ListValue(
                values=[
                    _ast.StringValue(value="FOO"),
                    _ast.StringValue(value="BAR"),
                ]
            ),
        ),
        (
            ["HELLO", "GOODBYE"],
            ListType(Enum),
            _ast.ListValue(
                values=[
                    _ast.EnumValue(value="HELLO"),
                    _ast.EnumValue(value="GOODBYE"),
                ]
            ),
        ),
        ("FOO", ListType(String), _ast.StringValue(value="FOO")),
    ],
)
def test_ast_node_from_value_with_list_types(value, input_type, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected)) as exc_info:
            ast_node_from_value(value, input_type)
        assert str(expected) == str(exc_info.value)
    else:
        assert ast_node_from_value(value, input_type) == expected


InputObject = InputObjectType(
    "MyInputObj",
    [InputField("foo", Float), InputField("bar", NonNullType(Enum))],
)


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            {"foo": 3, "bar": "HELLO"},
            _ast.ObjectValue(
                fields=[
                    _ast.ObjectField(
                        name=_ast.Name(value="foo"),
                        value=_ast.IntValue(value="3"),
                    ),
                    _ast.ObjectField(
                        name=_ast.Name(value="bar"),
                        value=_ast.EnumValue(value="HELLO"),
                    ),
                ]
            ),
        ),
        (
            {"foo": None, "bar": "HELLO"},
            _ast.ObjectValue(
                fields=[
                    _ast.ObjectField(
                        name=_ast.Name(value="foo"), value=_ast.NullValue()
                    ),
                    _ast.ObjectField(
                        name=_ast.Name(value="bar"),
                        value=_ast.EnumValue(value="HELLO"),
                    ),
                ]
            ),
        ),
        (
            {"bar": "HELLO"},
            _ast.ObjectValue(
                fields=[
                    _ast.ObjectField(
                        name=_ast.Name(value="bar"),
                        value=_ast.EnumValue(value="HELLO"),
                    )
                ]
            ),
        ),
        (42, ValueError('Value of type "MyInputObj" must be a dict')),
        ({}, ValueError('Field "bar" of type "MyInputObj" is required')),
    ],
)
def test_ast_node_from_value_with_objects(value, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected)) as exc_info:
            ast_node_from_value(value, InputObject)
        assert str(expected) == str(exc_info.value)
    else:
        assert ast_node_from_value(value, InputObject) == expected
