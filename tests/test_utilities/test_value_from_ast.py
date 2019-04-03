# -*- coding: utf-8 -*-

import uuid

import pytest

from py_gql.exc import InvalidValue, UnknownVariable
from py_gql.lang.parser import parse_value
from py_gql.schema.scalars import ID, UUID, Boolean, Float, Int, String
from py_gql.schema.types import (
    EnumType,
    EnumValue,
    InputField,
    InputObjectType,
    ListType,
    NonNullType,
)
from py_gql.utilities import untyped_value_from_ast, value_from_ast


class TestUntyped:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("null", None),
            ("true", True),
            ("false", False),
            ("123", 123),
            ("123.456", 123.456),
            ('"abc123"', "abc123"),
        ],
    )
    def test_it_parses_simple_values(self, value, expected):
        assert untyped_value_from_ast(parse_value(value)) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("[true, false]", [True, False]),
            ("[true, 123.45]", [True, 123.45]),
            ("[true, null]", [True, None]),
            ('[true, ["foo", 1.2]]', [True, ["foo", 1.2]]),
        ],
    )
    def test_it_parses_list_values(self, value, expected):
        assert untyped_value_from_ast(parse_value(value)) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("{ int: 123, bool: false }", {"int": 123, "bool": False}),
            ('{ foo: [ { bar: "baz"} ] }', {"foo": [{"bar": "baz"}]}),
        ],
    )
    def test_it_parses_input_objects(self, value, expected):
        assert untyped_value_from_ast(parse_value(value)) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("TEST_ENUM_VALUE", "TEST_ENUM_VALUE"),
            ("[TEST_ENUM_VALUE]", ["TEST_ENUM_VALUE"]),
        ],
    )
    def test_it_parses_enum_values_as_plain_strings(self, value, expected):
        assert untyped_value_from_ast(parse_value(value)) == expected

    @pytest.mark.parametrize(
        "value,variables,expected",
        [
            ("$testVariable", {"testVariable": "foo"}, "foo"),
            ("[$testVariable]", {"testVariable": "foo"}, ["foo"]),
            ("{a:[$testVariable]}", {"testVariable": "foo"}, {"a": ["foo"]}),
            ("$testVariable", {"testVariable": None}, None),
        ],
    )
    def test_it_parses_variables(self, value, variables, expected):
        assert untyped_value_from_ast(parse_value(value), variables) == expected

    def test_it_raises_on_unknown_variables(self):
        with pytest.raises(UnknownVariable) as exc_info:
            untyped_value_from_ast(parse_value("$testVariable"), {})
        assert str(exc_info.value) == "testVariable"


Color = EnumType(
    "Color",
    [
        EnumValue("RED", 1, ""),
        EnumValue("GREEN", 2, ""),
        EnumValue("BLUE", 3, ""),
        EnumValue("NULL", None, ""),
    ],
)


ListOfBool = ListType(Boolean)
NonNullBool = NonNullType(Boolean)
ListOfNonNullBool = ListType(NonNullType(Boolean))
NonNullListOfBool = NonNullType(ListType(Boolean))
NonNullListOfNonNullBool = NonNullType(ListType(NonNullType(Boolean)))


TestInput = InputObjectType(
    "TestInput",
    [
        InputField("int", Int, default_value=42),
        InputField("bool", Boolean),
        InputField("requiredBool", NonNullBool),
    ],
)


class TestTyped:
    def _run_test_case(self, value, type_, expected, error, variables=None):
        if error is None:
            assert (
                value_from_ast(parse_value(value), type_, variables) == expected
            )
        else:
            with pytest.raises(error):
                value_from_ast(parse_value(value), type_, variables)

    @pytest.mark.parametrize(
        "type_,value,expected",
        [
            (Boolean, "true", True),
            (Boolean, "false", False),
            (Int, "123", 123),
            (Float, "123", 123),
            (Float, "123.456", 123.456),
            (String, '"abc123"', "abc123"),
            (ID, "123456", "123456"),
            (ID, '"123456"', "123456"),
            (
                UUID,
                '"aacefca9-41c6-4a01-b372-632b4dc2506c"',
                uuid.UUID("aacefca9-41c6-4a01-b372-632b4dc2506c"),
            ),
            (
                UUID,
                '"AACEFCA9-41C6-4A01-B372-632B4DC2506C"',
                uuid.UUID("aacefca9-41c6-4a01-b372-632b4dc2506c"),
            ),
        ],
    )
    def test_it_converts_according_to_input_coercion_rules(
        self, type_, value, expected
    ):
        self._run_test_case(value, type_, expected, None)

    @pytest.mark.parametrize(
        "type_,value",
        [
            (Boolean, "123"),
            (Int, "123.456"),
            (Int, "true"),
            (Int, '"123"'),
            (Float, '"123"'),
            (String, "123"),
            (String, "true"),
            (ID, "123.456"),
            (UUID, "123.456"),
        ],
    )
    def test_it_does_not_convert_when_input_coercion_rules_reject_a_value(
        self, type_, value
    ):
        self._run_test_case(value, type_, None, InvalidValue)

    @pytest.mark.parametrize(
        "value,expected,error",
        [
            ("RED", 1, None),
            ("BLUE", 3, None),
            ("3", None, InvalidValue),
            ('"BLUE"', None, InvalidValue),
            ("NULL", None, None),
            ("UNDEFINED", None, InvalidValue),
        ],
    )
    def test_it_converts_enum_values_according_to_input_coercion_rules(
        self, value, expected, error
    ):
        self._run_test_case(value, Color, expected, error)

    def test_it_coerces_nullable_to_none(self):
        assert value_from_ast(parse_value("null"), Boolean, None) is None

    def test_it_raises_on_non_nullable_null(self):
        with pytest.raises(InvalidValue):
            value_from_ast(parse_value("null"), NonNullType(Boolean), None)

    @pytest.mark.parametrize(
        "type_,value,expected,error",
        [
            (ListOfBool, "true", [True], None),
            (ListOfBool, "[true]", [True], None),
            (ListOfBool, "123", None, InvalidValue),
            (ListOfBool, "null", None, None),
            (ListOfBool, "[true, false]", [True, False], None),
            (ListOfBool, "[true, 123]", None, InvalidValue),
            (ListOfBool, "[true, null]", [True, None], None),
            (ListOfBool, "{ true: true }", None, InvalidValue),
        ],
    )
    def test_it_coerces_lists_of_values(self, type_, value, expected, error):
        self._run_test_case(value, type_, expected, error)

    @pytest.mark.parametrize(
        "type_,value,expected,error",
        [
            (ListOfBool, "true", [True], None),
            (ListOfBool, "[true]", [True], None),
            (NonNullListOfBool, "123", None, InvalidValue),
            (NonNullListOfBool, "null", None, InvalidValue),
            (NonNullListOfBool, "[true, false]", [True, False], None),
            (NonNullListOfBool, "[true, 123]", None, InvalidValue),
            (NonNullListOfBool, "[true, null]", [True, None], None),
        ],
    )
    def test_it_coerces_non_null_lists_of_values(
        self, type_, value, expected, error
    ):
        self._run_test_case(value, type_, expected, error)

    @pytest.mark.parametrize(
        "type_,value,expected,error",
        [
            (ListOfBool, "true", [True], None),
            (ListOfBool, "[true]", [True], None),
            (ListOfNonNullBool, "123", None, InvalidValue),
            (ListOfNonNullBool, "null", None, None),
            (ListOfNonNullBool, "[true, false]", [True, False], None),
            (ListOfNonNullBool, "[true, 123]", None, InvalidValue),
            (ListOfNonNullBool, "[true, null]", None, InvalidValue),
        ],
    )
    def test_it_coerces_lists_of_non_null_values(
        self, type_, value, expected, error
    ):
        self._run_test_case(value, type_, expected, error)

    @pytest.mark.parametrize(
        "type_,value,expected,error",
        [
            (ListOfBool, "true", [True], None),
            (ListOfBool, "[true]", [True], None),
            (NonNullListOfNonNullBool, "123", None, InvalidValue),
            (NonNullListOfNonNullBool, "null", None, InvalidValue),
            (NonNullListOfNonNullBool, "[true, false]", [True, False], None),
            (NonNullListOfNonNullBool, "[true, 123]", None, InvalidValue),
            (NonNullListOfNonNullBool, "[true, null]", None, InvalidValue),
        ],
    )
    def test_it_coerces_non_null_lists_of_non_null_values(
        self, type_, value, expected, error
    ):
        self._run_test_case(value, type_, expected, error)

    @pytest.mark.parametrize(
        "type_,value,expected,error",
        [
            (TestInput, "null", None, None),
            (TestInput, "123", None, InvalidValue),
            (TestInput, "[]", None, InvalidValue),
            (
                TestInput,
                "{ int: 123, requiredBool: false }",
                {"int": 123, "requiredBool": False},
                None,
            ),
            (
                TestInput,
                "{ bool: true, requiredBool: false }",
                {"int": 42, "bool": True, "requiredBool": False},
                None,
            ),
            (
                TestInput,
                "{ int: true, requiredBool: true }",
                None,
                InvalidValue,
            ),
            (TestInput, "{ requiredBool: null }", None, InvalidValue),
            (TestInput, "{ bool: true }", None, InvalidValue),
        ],
    )
    def test_it_coerces_input_object(self, type_, value, expected, error):
        self._run_test_case(value, type_, expected, error)

    @pytest.mark.parametrize(
        "type_,value,variables,expected,error",
        [
            (Boolean, "$var", {}, None, InvalidValue),
            (Boolean, "$var", {"var": True}, True, None),
            (Boolean, "$var", {"var": None}, None, None),
        ],
    )
    def test_it_accepts_variable_values_assuming_already_coerced(
        self, type_, value, variables, expected, error
    ):
        self._run_test_case(value, type_, expected, error, variables)

    def test_it_raises_on_null_variable_with_non_null_type(self):
        with pytest.raises(InvalidValue) as exc_info:
            value_from_ast(
                parse_value("$testVariable"),
                NonNullBool,
                {"testVariable": None},
            )

        assert str(exc_info.value) == (
            'Variable "$testVariable" used for type "Boolean!" '
            "must not be null."
        )

    @pytest.mark.parametrize(
        "type_,value,variables,expected,error",
        [
            # We fail hard on missing variables
            # (ListOfBool, ' [ $foo ]', {}, [None], None),
            (ListOfBool, " [ $foo ]", {}, None, UnknownVariable),
            (ListOfNonNullBool, " [ $foo ]", {}, None, InvalidValue),
            (ListOfNonNullBool, " [ $foo ]", {"foo": True}, [True], None),
            # Note: variables are expected to have already been coerced, so we
            # do not expect the singleton wrapping behavior for variables.
            (ListOfNonNullBool, "$foo", {"foo": True}, True, None),
            (ListOfNonNullBool, "$foo", {"foo": [True]}, [True], None),
        ],
    )
    def test_it_asserts_variables_are_provided_as_items_in_lists(
        self, type_, value, variables, expected, error
    ):
        self._run_test_case(value, type_, expected, error, variables)

    @pytest.mark.parametrize(
        "type_,value,variables,expected,error",
        [
            # We fail hard on missing variables
            # (TestInput, '{ int: $foo, bool: $foo, requiredBool: true }', {}, {
            #     'int': 42,
            #     'requiredBool': True,
            # }, None),
            (
                TestInput,
                "{ int: $foo, bool: $foo, requiredBool: true }",
                {},
                None,
                UnknownVariable,
            ),
            (TestInput, "{ requiredBool: $foo }", {}, None, UnknownVariable),
            (
                TestInput,
                "{ requiredBool: $foo, bool: $foo }",
                {"foo": True},
                {"int": 42, "requiredBool": True, "bool": True},
                None,
            ),
        ],
    )
    def test_it_omits_input_object_fields_for_unprovided_variables(
        self, type_, value, variables, expected, error
    ):
        self._run_test_case(value, type_, expected, error, variables)
