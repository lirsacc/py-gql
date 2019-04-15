# -*- coding: utf-8 -*-

import pytest

from py_gql.exc import CoercionError
from py_gql.schema import (
    EnumType,
    Float,
    InputField,
    InputObjectType,
    Int,
    ListType,
    NonNullType,
    String,
)
from py_gql.utilities import coerce_value


def _test(value, type_, expected_result, expected_error=None):
    if expected_error is not None:
        with pytest.raises(CoercionError) as exc_info:
            coerce_value(value, type_)
        assert str(exc_info.value) == expected_error
    else:
        assert coerce_value(value, type_) == expected_result


def test_String_raises_on_list():
    _test(
        [1, 2, 3],
        String,
        None,
        'String cannot represent list value "[1, 2, 3]"',
    )


def test_Int_from_int_input():
    _test("1", Int, 1)


def test_Int_from_int_input_1():
    _test(1, Int, 1)


def test_Int_from_negative_int_input():
    _test("-1", Int, -1)


def test_Int_from_exponent_input():
    _test("1e3", Int, 1e3)


def test_Int_from_null_value():
    _test(None, Int, None)


def test_Int_raises_for_empty_value():
    _test(
        "", Int, None, "Int cannot represent non integer value: (empty string)"
    )


def test_Int_raises_for_float_input():
    _test("1.5", Int, None, "Int cannot represent non integer value: 1.5")


def test_Int_raises_for_char_input():
    _test("c", Int, None, "Int cannot represent non integer value: c")


def test_Int_raises_for_string_input():
    _test("meow", Int, None, "Int cannot represent non integer value: meow")


def test_Float_for_int_input():
    _test("1", Float, 1.0)


def test_Float_for_exponent_input():
    _test("1e3", Float, 1e3)


def test_Float_for_float_input():
    _test("1.5", Float, 1.5)


def test_Float_raises_for_empty_value():
    _test(
        "",
        Float,
        None,
        "Float cannot represent non numeric value: (empty string)",
    )


def test_Float_raises_for_char_input():
    _test("a", Float, None, "Float cannot represent non numeric value: a")


def test_Float_raises_for_string_input():
    _test("meow", Float, None, "Float cannot represent non numeric value: meow")


Enum = EnumType("TestEnum", [("FOO", "InternalFoo"), ("BAR", 123456789)])


def test_Enum_for_a_known_enum_names():
    _test("FOO", Enum, "InternalFoo")
    _test("BAR", Enum, 123456789)


def test_Enum_raises_for_misspelled_enum_value():
    _test("foo", Enum, None, "Invalid name foo for enum TestEnum")


def test_Enum_raises_for_incorrect_value_type():
    _test(123, Enum, None, "Expected type TestEnum")


Input = InputObjectType(
    "TestInputObject",
    [InputField("foo", NonNullType(Int)), InputField("bar", Int)],
)


def test_InputObject_for_valid_input():
    _test({"foo": 123}, Input, {"foo": 123})


def test_InputObject_raises_for_non_dict_input():
    _test(123, Input, None, "Expected type TestInputObject to be an object")


def test_InputObject_raises_for_invalid_field():
    _test(
        {"foo": "abc"},
        Input,
        None,
        "Int cannot represent non integer value: abc at value.foo",
    )


def test_InputObject_raises_for_missing_required_field():
    _test(
        {},
        Input,
        None,
        "Field foo of required type Int! was not provided at value.foo",
    )


def test_InputObject_raises_for_unknown_field():
    _test(
        {"foo": 1, "baz": 1},
        Input,
        None,
        "Field baz is not defined by type TestInputObject",
    )


def test_ListType_for_single_valid_value():
    _test("1", ListType(Int), [1])


def test_ListType_for_valid_values():
    _test([1, "2", "3"], ListType(Int), [1, 2, 3])


def test_ListType_raises_for_invalid_item():
    _test(
        [1, "abc", "3"],
        ListType(Int),
        None,
        "Int cannot represent non integer value: abc at value[1]",
    )


def test_ListType_raises_for_invalid_items():
    _test(
        [1, "abc", "def"],
        ListType(Int),
        None,
        "Int cannot represent non integer value: abc at value[1],\n"
        "Int cannot represent non integer value: def at value[2]",
    )


def test_nested_error():
    _test(
        [{"foo": "abc"}],
        ListType(Input),
        None,
        "Int cannot represent non integer value: abc at value[0].foo",
    )


def test_null_non_nullable_type():
    _test(
        None,
        NonNullType(Int),
        None,
        "Expected non-nullable type Int! not to be null",
    )
