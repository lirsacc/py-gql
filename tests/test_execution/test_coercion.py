# -*- coding: utf-8 -*-
""" tests related to how raw JSON variables are coerced
and forwared to the execution context """

import json

import pytest

from py_gql.exc import VariablesCoercionError
from py_gql.schema import (
    Argument,
    Field,
    InputField,
    InputObjectType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    String,
)

from ._test_utils import assert_sync_execution

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


def _complex_parse(value):
    if value == "SerializedValue":
        return "DeserializedValue"
    raise ValueError(value)


ComplexScalar = ScalarType("ComplexScalar", _complex_parse, _complex_parse)

TestInputObject = InputObjectType(
    "TestInputObject",
    [
        InputField("a", String),
        InputField("b", ListType(String)),
        InputField("c", NonNullType(String)),
        InputField("d", ComplexScalar),
    ],
)

TestNestedInputObject = InputObjectType(
    "TestNestedInputObject",
    [
        InputField("na", NonNullType(TestInputObject)),
        InputField("nb", NonNullType(String)),
    ],
)


def _inspect(name):
    def _inspect_resolver(*_, **args):
        return json.dumps(args.get(name, None), sort_keys=True)

    return _inspect_resolver


_field = lambda name, argType, **kw: Field(
    name, String, [Argument("input", argType, **kw)], resolver=_inspect("input")
)

TestType = ObjectType(
    "TestType",
    [
        _field("fieldWithObjectInput", TestInputObject),
        _field("fieldWithNullableStringInput", String),
        _field("fieldWithNonNullableStringInput", NonNullType(String)),
        _field(
            "fieldWithNonNullableStringInputAndDefaultArgumentValue",
            NonNullType(String),
            default_value="Hello World",
        ),
        _field(
            "fieldWithDefaultArgumentValue", String, default_value="Hello World"
        ),
        _field("fieldWithNestedObjectInput", TestNestedInputObject),
        _field("list", ListType(String)),
        _field("nnList", NonNullType(ListType(String))),
        _field("listNN", ListType(NonNullType(String))),
        _field("nnListNN", NonNullType(ListType(NonNullType(String)))),
    ],
)

_SCHEMA = Schema(TestType)


async def test_complex_input_inline_struct():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithObjectInput(input: {a: "foo", b: ["bar"], c: "baz"})
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"a": "foo", "b": ["bar"], "c": "baz"}'
        },
        expected_errors=[],
    )


async def test_single_value_to_list_inline_struct():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithObjectInput(input: {a: "foo", b: "bar", c: "baz"})
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"a": "foo", "b": ["bar"], "c": "baz"}'
        },
        expected_errors=[],
    )


async def test_null_value_inline_struct():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithObjectInput(input: {a: null, b: null, c: "C", d: null})
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"a": null, "b": null, "c": "C", "d": null}'
        },
        expected_errors=[],
    )


async def test_null_value_in_list_inline_struct():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithObjectInput(input: {b: ["A",null,"C"], c: "C"})
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"b": ["A", null, "C"], "c": "C"}'
        },
        expected_errors=[],
    )


async def test_does_not_use_incorrect_value_inline_struct():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithObjectInput(input: ["foo", "bar", "baz"])
        }
        """,
        expected_data={"fieldWithObjectInput": None},
        expected_errors=[
            (
                'Argument "input" of type "TestInputObject" was provided invalid '
                'value ["foo", "bar", "baz"] (Expected Object but got ListValue)',
                (6, 56),
                "fieldWithObjectInput",
            )
        ],
    )


async def test_uses_parse_literal_on_scalar_types_inline_struct():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithObjectInput(input: {c: "foo", d: "SerializedValue"})
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"c": "foo", "d": "DeserializedValue"}'
        },
        expected_errors=[],
    )


async def test_complex_input_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"a": "foo", "b": ["bar"], "c": "baz"}'
        },
        expected_errors=[],
        variables={"input": {"a": "foo", "b": ["bar"], "c": "baz"}},
    )


async def test_uses_default_value_when_not_provided():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject = {a: "foo", b: ["bar"], c: "baz"}) {
            fieldWithObjectInput(input: $input)
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"a": "foo", "b": ["bar"], "c": "baz"}'
        },
        expected_errors=[],
        variables={},
    )


async def test_single_value_to_list_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"a": "foo", "b": ["bar"], "c": "baz"}'
        },
        expected_errors=[],
        variables={"input": {"a": "foo", "b": "bar", "c": "baz"}},
    )


async def test_complex_scalar_input_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        expected_data={
            "fieldWithObjectInput": '{"c": "foo", "d": "DeserializedValue"}'
        },
        expected_errors=[],
        variables={"input": {"c": "foo", "d": "SerializedValue"}},
    )


async def test_error_on_null_for_nested_non_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        variables={"input": {"a": "foo", "b": "bar", "c": None}},
        expected_exc=(
            VariablesCoercionError,
            (
                'Variable "$input" got invalid value '
                '{"a": "foo", "b": "bar", "c": null} (Expected non-nullable type '
                "String! not to be null at value.c)"
            ),
        ),
    )


async def test_error_on_incorrect_type():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        variables={"input": "foo bar"},
        expected_exc=(
            VariablesCoercionError,
            (
                'Variable "$input" got invalid value "foo bar" (Expected type '
                "TestInputObject to be an object)"
            ),
        ),
    )


async def test_errors_on_omission_of_nested_non_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        variables={"input": {"a": "foo", "b": "bar"}},
        expected_exc=(
            VariablesCoercionError,
            (
                'Variable "$input" got invalid value {"a": "foo", "b": "bar"} '
                "(Field c of required type String! was not provided at value.c)"
            ),
        ),
    )


async def test_fail_on_deep_nested_errors_with_multiple_errors():
    with pytest.raises(VariablesCoercionError) as exc_info:
        assert_sync_execution(
            _SCHEMA,
            """
            query ($input: TestNestedInputObject) {
                fieldWithNestedObjectInput(input: $input)
            }
            """,
            variables={"input": {"na": {"a": "foo"}}},
        )

    assert str(exc_info.value) == (
        'Variable "$input" got invalid value {"na": {"a": "foo"}} '
        "(Field c of required type String! was not provided at value.na.c),\n"
        'Variable "$input" got invalid value {"na": {"a": "foo"}} '
        "(Field nb of required type String! was not provided at value.nb)"
    )


async def test_fail_on_addition_of_unknown_input_field():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        """,
        variables={
            "input": {"a": "foo", "b": "bar", "c": "baz", "extra": "dog"}
        },
        expected_exc=(
            VariablesCoercionError,
            (
                'Variable "$input" got invalid value {"a": "foo", "b": "bar", "c": '
                '"baz", "extra": "dog"} (Field extra is not defined by type '
                "TestInputObject)"
            ),
        ),
    )


async def test_allows_nullable_inputs_to_be_omitted():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithNullableStringInput
        }
        """,
        expected_data={"fieldWithNullableStringInput": "null"},
        expected_errors=[],
    )


async def test_allows_nullable_inputs_to_be_omitted_in_a_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String) {
            fieldWithNullableStringInput(input: $value)
        }
        """,
        expected_data={"fieldWithNullableStringInput": "null"},
        expected_errors=[],
    )


async def test_allows_nullable_inputs_to_be_set_to_null_in_a_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String) {
            fieldWithNullableStringInput(input: $value)
        }
        """,
        expected_data={"fieldWithNullableStringInput": "null"},
        expected_errors=[],
        variables={"value": None},
    )


async def test_allows_nullable_inputs_to_be_set_to_a_value_in_a_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String) {
            fieldWithNullableStringInput(input: $value)
        }
        """,
        expected_data={"fieldWithNullableStringInput": '"a"'},
        expected_errors=[],
        variables={"value": "a"},
    )


async def test_allows_nullable_inputs_to_be_set_to_a_value_directly():
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithNullableStringInput(input: "a")
        }
        """,
        expected_data={"fieldWithNullableStringInput": '"a"'},
        expected_errors=[],
    )


async def test_allows_non_nullable_inputs_to_be_omitted_given_a_default():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String = "default") {
            fieldWithNonNullableStringInput(input: $value)
        }
        """,
        expected_data={"fieldWithNonNullableStringInput": '"default"'},
        expected_errors=[],
    )


async def test_does_not_allow_non_nullable_inputs_to_be_omitted_in_a_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        """,
        expected_exc=(
            VariablesCoercionError,
            'Variable "$value" of required type "String!" was not provided.',
        ),
    )


async def test_does_not_allow_non_nullable_inputs_to_be_set_to_null_in_a_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        """,
        variables={"input": None},
        expected_exc=(
            VariablesCoercionError,
            'Variable "$value" of required type "String!" was not provided.',
        ),
    )


async def test_allows_non_nullable_inputs_to_be_set_to_a_value_in_a_variable():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        """,
        expected_data={"fieldWithNonNullableStringInput": '"a"'},
        expected_errors=[],
        variables={"value": "a"},
    )


async def test_allows_non_nullable_inputs_to_be_set_to_a_value_directly():
    assert_sync_execution(
        _SCHEMA,
        """
        query {
            fieldWithNonNullableStringInput(input: "a")
        }
        """,
        expected_data={"fieldWithNonNullableStringInput": '"a"'},
        expected_errors=[],
    )


async def test_reports_error_for_missing_non_nullable_inputs():
    assert_sync_execution(
        _SCHEMA,
        "{ fieldWithNonNullableStringInput }",
        expected_data={"fieldWithNonNullableStringInput": None},
        expected_errors=[
            (
                'Argument "input" of required type "String!" was not provided',
                (2, 33),
                "fieldWithNonNullableStringInput",
            )
        ],
    )


async def test_reports_error_for_array_passed_into_string_input():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        """,
        variables={"value": [1, 2, 3]},
        expected_exc=(
            VariablesCoercionError,
            (
                'Variable "$value" got invalid value [1, 2, 3] (String cannot '
                'represent list value "[1, 2, 3]")'
            ),
        ),
    )


async def test_reports_error_for_non_provided_variables_for_non_nullable_inputs():
    # This is an *invalid* query, but it should be an *executable* query.
    assert_sync_execution(
        _SCHEMA,
        """
        {
            fieldWithNonNullableStringInput(input: $foo)
        }
        """,
        variables={"value": [1, 2, 3]},
        expected_data={"fieldWithNonNullableStringInput": None},
        expected_errors=[
            (
                'Argument "input" of required type "String!" was provided the '
                'missing variable "$foo"',
                (6, 50),
                "fieldWithNonNullableStringInput",
            )
        ],
    )


async def test_uses_default_when_no_runtime_value_is_provided_to_a_non_null_argument():
    assert_sync_execution(
        _SCHEMA,
        """
        query optionalVariable($optional: String) {
            fieldWithNonNullableStringInputAndDefaultArgumentValue(input: $optional)
        }
        """,
        expected_data={
            "fieldWithNonNullableStringInputAndDefaultArgumentValue": '"Hello World"'
        },
        expected_errors=[],
    )


async def test_allows_lists_to_be_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String]) {
            list(input: $input)
        }
        """,
        expected_data={"list": "null"},
        expected_errors=[],
        variables={"input": None},
    )


async def test_allows_lists_to_contain_values():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String]) {
            list(input: $input)
        }
        """,
        expected_data={"list": '["A"]'},
        expected_errors=[],
        variables={"input": ["A"]},
    )


async def test_allows_lists_to_contain_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String]) {
            list(input: $input)
        }
        """,
        expected_data={"list": '["A", null, "B"]'},
        expected_errors=[],
        variables={"input": ["A", None, "B"]},
    )


async def test_does_not_allow_non_null_lists_to_be_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String]!) {
            nnList(input: $input)
        }
        """,
        expected_exc=(
            VariablesCoercionError,
            'Variable "$input" of required type "[String]!" must not be null.',
        ),
        variables={"input": None},
    )


async def test_allows_non_null_lists_to_contain_values():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String]!) {
            nnList(input: $input)
        }
        """,
        expected_data={"nnList": '["A"]'},
        expected_errors=[],
        variables={"input": ["A"]},
    )


async def test_allows_non_null_lists_to_contain_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String]!) {
            nnList(input: $input)
        }
        """,
        expected_data={"nnList": '["A", null, "B"]'},
        expected_errors=[],
        variables={"input": ["A", None, "B"]},
    )


async def test_does_not_allow_non_null_lists_of_non_nulls_to_be_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String!]!) {
            nnListNN(input: $input)
        }
        """,
        variables={"input": None},
        expected_exc=(
            VariablesCoercionError,
            'Variable "$input" of required type "[String!]!" must not be null.',
        ),
    )


async def test_allows_non_null_lists_of_non_nulls_to_contain_values():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String!]!) {
            nnListNN(input: $input)
        }
        """,
        variables={"input": ["A"]},
        expected_data={"nnListNN": '["A"]'},
        expected_errors=[],
    )


async def test_does_not_allow_non_null_lists_of_non_nulls_to_contain_null():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($input: [String!]!) {
            nnListNN(input: $input)
        }
        """,
        variables={"input": ["A", None, "B"]},
        expected_exc=(
            VariablesCoercionError,
            (
                'Variable "$input" got invalid value ["A", null, "B"] (Expected '
                "non-nullable type String! not to be null at value[1])"
            ),
        ),
    )


async def test_does_not_allow_invalid_types_to_be_used_as_values():
    with pytest.raises(VariablesCoercionError) as exc_info:
        assert_sync_execution(
            _SCHEMA,
            """
        query ($input: TestType!) {
            fieldWithObjectInput(input: $input)
        }""",
            variables={"input": ["A", "B"]},
        )

    assert (
        'Variable "$input" expected value of type "TestType!" which cannot be used as '
        "an input type." in str(exc_info.value)
    )


async def test_does_not_allow_unknown_types_to_be_used_as_values():
    with pytest.raises(VariablesCoercionError) as exc_info:
        assert_sync_execution(
            _SCHEMA,
            """
        query ($input: UnknownType!) {
            fieldWithObjectInput(input: $input)
        }""",
            variables={"input": "whoknows"},
        )

    assert 'Unknown type "UnknownType!" for variable "$input"' in str(
        exc_info.value
    )


async def test_argument_default_values_when_no_argument_provided():
    assert_sync_execution(
        _SCHEMA,
        "{ fieldWithDefaultArgumentValue }",
        expected_data={"fieldWithDefaultArgumentValue": '"Hello World"'},
        expected_errors=[],
    )


async def test_argument_default_values_when_omitted_variable_provided():
    assert_sync_execution(
        _SCHEMA,
        """
        query ($optional: String) {
            fieldWithDefaultArgumentValue(input: $optional)
        }
        """,
        expected_data={"fieldWithDefaultArgumentValue": '"Hello World"'},
        expected_errors=[],
    )


async def test_argument_default_value_when_argument_cannot_be_coerced():
    # This is an *invalid* query, but it should be an *executable* query.
    assert_sync_execution(
        _SCHEMA,
        "{ fieldWithDefaultArgumentValue(input: WRONG_TYPE) }",
        expected_data={"fieldWithDefaultArgumentValue": None},
        expected_errors=[
            (
                'Argument "input" of type "String" was provided '
                "invalid value WRONG_TYPE (Invalid literal EnumValue for "
                "scalar type String)",
                (2, 50),
                "fieldWithDefaultArgumentValue",
            )
        ],
    )


class TestNonNullArguments:
    schema_with_null_args = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "withNonNullArg",
                    String,
                    args=[Argument("cannotBeNull", NonNullType(String))],
                    resolver=lambda *_, **args: json.dumps(
                        args.get("cannotBeNull", "NOT PROVIDED")
                    ),
                )
            ],
        )
    )

    async def test_non_null_literal(self):
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query {
                withNonNullArg (cannotBeNull: "literal value")
            }
            """,
            expected_data={"withNonNullArg": '"literal value"'},
            expected_errors=[],
        )

    async def test_non_null_variable(self):
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String!) {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            variables={"testVar": "variable value"},
            expected_data={"withNonNullArg": '"variable value"'},
            expected_errors=[],
        )

    async def test_missing_variable_with_default(self):
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String = "default value") {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            expected_data={"withNonNullArg": '"default value"'},
            expected_errors=[],
        )

    async def test_missing(self):
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query {
                withNonNullArg
            }
            """,
            expected_data={"withNonNullArg": None},
            expected_errors=[
                (
                    'Argument "cannotBeNull" of required type "String!" was '
                    "not provided",
                    (12, 26),
                    "withNonNullArg",
                )
            ],
        )

    async def test_null_literal(self):
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query {
                withNonNullArg (cannotBeNull: null)
            }
            """,
            expected_data={"withNonNullArg": None},
            expected_errors=[
                (
                    'Argument "cannotBeNull" of type "String!" was provided '
                    "invalid value null (Expected non null value.)",
                    (12, 47),
                    "withNonNullArg",
                )
            ],
        )

    async def test_missing_variable(self):
        # Differs from reference implementation as a missing variable will
        # abort the full execution. This is consistent as all variables defined
        # must be used in an operation and so a missing variables for a non null
        # type should break.
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String!) {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            expected_exc=(
                VariablesCoercionError,
                (
                    'Variable "$testVar" of required type "String!" was not '
                    "provided."
                ),
            ),
        )

    async def test_null_variable(self):
        # Differs from reference implementation as a null variable provided for
        # a non null type will abort the full execution.
        assert_sync_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String!) {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            variables={"testVar": None},
            expected_exc=(
                VariablesCoercionError,
                (
                    'Variable "$testVar" of required type "String!" '
                    "must not be null."
                ),
            ),
        )
