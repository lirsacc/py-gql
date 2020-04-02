# -*- coding: utf-8 -*-
"""
Test type definition classes.
"""

import enum

import pytest

from py_gql.exc import ScalarSerializationError, UnknownEnumValue
from py_gql.schema import (
    Boolean,
    EnumType,
    Float,
    Int,
    ListType,
    NonNullType,
    String,
)


def test_as_list():
    assert String.as_list() == ListType(String)


def test_as_non_null():
    assert String.as_non_null() == NonNullType(String)


def test_EnumType_rejects_duplicate_names():
    with pytest.raises(ValueError):
        EnumType("Enum", [("SOME_NAME", 1), ("SOME_NAME", 2)])


@pytest.mark.parametrize("name", ["null", "true", "false"])
def test_EnumValue_rejects_forbidden_name(name):
    with pytest.raises(ValueError):
        EnumType("Enum", [name])


def test_EnumType_get_value_ok():
    t = EnumType("Enum", [("SOME_NAME", 1)])
    assert t.get_value("SOME_NAME") == 1


def test_EnumType_get_value_fail():
    t = EnumType("Enum", [("SOME_NAME", 1)])
    with pytest.raises(UnknownEnumValue) as exc_info:
        t.get_value("SOME_OTHER_NAME")
    assert str(exc_info.value) == "Invalid name SOME_OTHER_NAME for enum Enum"


def test_EnumType_get_name_ok():
    t = EnumType("Enum", [("SOME_NAME", 1)])
    assert t.get_name(1) == "SOME_NAME"


def test_EnumType_get_name_fail():
    t = EnumType("Enum", [("SOME_NAME", 1)])
    with pytest.raises(UnknownEnumValue) as exc_info:
        t.get_name(2)
    assert str(exc_info.value) == "Invalid value 2 for enum Enum"


def test_EnumType_from_python_enum():
    class FooEnum(enum.Enum):
        A = "A"
        B = "B"
        C = "C"

    enum_type = EnumType.from_python_enum(FooEnum)

    for x in FooEnum:
        assert x is enum_type.get_value(x.name)
        assert enum_type.get_name(x) == x.name

    with pytest.raises(UnknownEnumValue):
        enum_type.get_value("D")


@pytest.mark.parametrize(
    "type_, input_, output",
    [
        (Int, 1, 1),
        (Int, "123", 123),
        (Int, 0, 0),
        (Int, -1, -1),
        (Int, 1e5, 100000),
        (Int, False, 0),
        (Int, True, 1),
        (Float, 1, 1.0),
        (Float, 0, 0.0),
        (Float, "123.5", 123.5),
        (Float, -1, -1.0),
        (Float, 0.1, 0.1),
        (Float, 1.1, 1.1),
        (Float, -1.1, -1.1),
        (Float, "-1.1", -1.1),
        (Float, False, 0.0),
        (Float, True, 1.0),
        (String, "string", "string"),
        (String, 1, "1"),
        (String, -1.1, "-1.1"),
        (String, True, "true"),
        (String, False, "false"),
        (Boolean, "string", True),
        (Boolean, "", False),
        (Boolean, 1, True),
        (Boolean, 0, False),
        (Boolean, True, True),
        (Boolean, False, False),
    ],
)
def test_scalar_serialization_ok(type_, input_, output):
    assert type_.serialize(input_) == output


@pytest.mark.parametrize(
    "type_, input_, err",
    [
        (Int, 0.1, "Int cannot represent non integer value: 0.1"),
        (Int, 1.1, "Int cannot represent non integer value: 1.1"),
        (Int, -1.1, "Int cannot represent non integer value: -1.1"),
        (Int, "-1.1", "Int cannot represent non integer value: -1.1"),
        (
            Int,
            9876504321,
            "Int cannot represent non 32-bit signed integer: 9876504321",
        ),
        (
            Int,
            "-9876504321",
            "Int cannot represent non 32-bit signed integer: -9876504321",
        ),
        (Int, "1e100", "Int cannot represent non 32-bit signed integer: 1e100"),
        (
            Int,
            "-1e100",
            "Int cannot represent non 32-bit signed integer: -1e100",
        ),
        (Int, "one", "Int cannot represent non integer value: one"),
        (Int, "", "Int cannot represent non integer value: (empty string)"),
        (Int, None, "Int cannot represent non integer value: None"),
        (Float, None, "Float cannot represent non numeric value: None"),
        (Float, "one", "Float cannot represent non numeric value: one"),
        (Float, "", "Float cannot represent non numeric value: (empty string)"),
    ],
)
def test_scalar_serialization_fail(type_, input_, err):
    with pytest.raises(ScalarSerializationError) as exc_info:
        type_.serialize(input_)
    assert str(exc_info.value) == err
