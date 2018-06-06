# -*- coding: utf-8 -*-
""" tests related to how raw JSON variables are coerced
and forwared to the execution context """

import json

import pytest

from py_gql.exc import VariableCoercionError, DocumentValidationError
from py_gql.schema import (
    Schema, ObjectType, InputObjectType, ListType, String, NonNullType,
    ScalarType, InputField, Arg, Field)
from ._test_utils import check_execution


def _complex_parse(value):
    if value == 'SerializedValue':
        return 'DeserializedValue'
    raise ValueError(value)


ComplexScalar = ScalarType('ComplexScalar', _complex_parse, _complex_parse)

TestInputObject = InputObjectType('TestInputObject', [
    InputField('a', String),
    InputField('b', ListType(String)),
    InputField('c', NonNullType(String)),
    InputField('d', ComplexScalar),
])

TestNestedInputObject = InputObjectType('TestNestedInputObject', [
    InputField('na', NonNullType(TestInputObject)),
    InputField('nb', NonNullType(String)),
])

_inspect = lambda _, args, *a: json.dumps(
    args.get('input', None), sort_keys=True
)

_field = lambda name, argType, **kw: Field(name, String, [
    Arg('input', argType, **kw),
], resolve=_inspect)

TestType = ObjectType('TestType', [
    _field('fieldWithObjectInput', TestInputObject),
    _field('fieldWithNullableStringInput', String),
    _field('fieldWithNonNullableStringInput', NonNullType(String)),
    _field(
        'fieldWithDefaultArgumentValue', String, default_value='Hello World'
    ),
    _field('fieldWithNestedObjectInput', TestNestedInputObject),
    _field('list', ListType(String)),
    _field('nnList', NonNullType(ListType(String))),
    _field('listNN', ListType(NonNullType(String))),
    _field('nnListNN', NonNullType(ListType(NonNullType(String)))),
])

_SCHEMA = Schema(TestType)


def test_complex_input_inline_struct():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithObjectInput(input: {a: "foo", b: ["bar"], c: "baz"})
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"a": "foo", "b": ["bar"], "c": "baz"}',
        },
        expected_errors=[]
    )


def test_single_value_to_list_inline_struct():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithObjectInput(input: {a: "foo", b: "bar", c: "baz"})
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"a": "foo", "b": ["bar"], "c": "baz"}',
        },
        expected_errors=[]
    )


def test_null_value_inline_struct():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithObjectInput(input: {a: null, b: null, c: "C", d: null})
        }
        ''',
        expected_data={
            'fieldWithObjectInput':
                '{"a": null, "b": null, "c": "C", "d": null}'
        },
        expected_errors=[]
    )


def test_null_value_in_list_inline_struct():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithObjectInput(input: {b: ["A",null,"C"], c: "C"})
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"b": ["A", null, "C"], "c": "C"}'
        },
        expected_errors=[]
    )


def test_does_not_use_incorrect_value_inline_struct():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithObjectInput(input: ["foo", "bar", "baz"])
        }
        ''',
        expected_data={
            'fieldWithObjectInput': None,
        },
        expected_errors=[
            ('Argument "input" of type "TestInputObject" was provided invalid '
             'value ["foo", "bar", "baz"] (Expected Object but got ListValue)',
             (23, 73), 'fieldWithObjectInput')
        ]
    )


def test_uses_parse_literal_on_scalar_types_inline_struct():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithObjectInput(input: {c: "foo", d: "SerializedValue"})
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"c": "foo", "d": "DeserializedValue"}'
        },
        expected_errors=[]
    )


def test_complex_input_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"a": "foo", "b": ["bar"], "c": "baz"}',
        },
        expected_errors=[],
        variables={
            'input': {
                'a': 'foo',
                'b': ['bar'],
                'c': 'baz'
            }
        }
    )


def test_uses_default_value_when_not_provided():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject = {a: "foo", b: ["bar"], c: "baz"}) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"a": "foo", "b": ["bar"], "c": "baz"}',
        },
        expected_errors=[],
        variables={}
    )


def test_single_value_to_list_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"a": "foo", "b": ["bar"], "c": "baz"}',
        },
        expected_errors=[],
        variables={
            'input': {
                'a': 'foo',
                'b': 'bar',
                'c': 'baz'
            }
        }
    )


def test_complex_scalar_input_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        expected_data={
            'fieldWithObjectInput': '{"c": "foo", "d": "DeserializedValue"}',
        },
        expected_errors=[],
        variables={
            'input': {
                'c': 'foo',
                'd': 'SerializedValue',
            }
        }
    )


def test_error_on_null_for_nested_non_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        variables={
            'input': {
                'a': 'foo',
                'b': 'bar',
                'c': None
            }
        },
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value '
            '{"a": "foo", "b": "bar", "c": null} (Expected non-nullable type '
            'String! not to be null at value.c)'
        )
    )


def test_error_on_incorrect_type():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        variables={
            'input': 'foo bar'
        },
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value "foo bar" (Expected type '
            'TestInputObject to be an object)'
        )
    )


def test_errors_on_omission_of_nested_non_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        variables={
            'input': {
                'a': 'foo',
                'b': 'bar',
            }
        },
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value {"a": "foo", "b": "bar"} '
            '(Field c of required type String! was not provided at value.c)'
        )
    )


# REVIEW: Difference with reference implementation
@pytest.mark.xfail
def test_fail_on_deep_nested_errors_and_with_many_errors():
    with pytest.raises(VariableCoercionError) as exc_info:
        check_execution(
            _SCHEMA, '''
            query ($input: TestNestedInputObject) {
                fieldWithNestedObjectInput(input: $input)
            }
            ''',
            variables={
                'input': {
                    'na': {
                        'a': 'foo',
                    }
                }
            }
        )

    assert exc_info.value.errors == [
        'Variable "$input" got invalid value {"na": {"a": "foo"}} (Field c of '
        'required type String! was not provided at value.na.c)',
        'Variable "$input" got invalid value {"na": {"a": "foo"}} '
        '(Field nb of required type String! was not provided at value.nb)'
    ]


def test_fail_on_addition_of_unknown_input_field():
    check_execution(
        _SCHEMA,
        '''
        query ($input: TestInputObject) {
            fieldWithObjectInput(input: $input)
        }
        ''',
        variables={
            'input': {
                'a': 'foo',
                'b': 'bar',
                'c': 'baz',
                'extra': 'dog',
            }
        },
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value {"a": "foo", "b": "bar", "c": '
            '"baz", "extra": "dog"} (Field extra is not defined by type '
            'TestInputObject)'
        )
    )


def test_allows_nullable_inputs_to_be_omitted():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithNullableStringInput
        }
        ''',
        expected_data={'fieldWithNullableStringInput': 'null'},
        expected_errors=[]
    )


def test_allows_nullable_inputs_to_be_omitted_in_a_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String) {
            fieldWithNullableStringInput(input: $value)
        }
        ''',
        expected_data={'fieldWithNullableStringInput': 'null'},
        expected_errors=[]
    )


def test_allows_nullable_inputs_to_be_omitted_in_an_unlisted_variable():
    # The query is not valid but should execute
    check_execution(
        _SCHEMA,
        '''
        query {
            fieldWithNullableStringInput(input: $value)
        }
        ''',
        expected_data={'fieldWithNullableStringInput': 'null'},
        expected_errors=[],
        _skip_validation=True
    )


def test_allows_nullable_inputs_to_be_set_to_null_in_a_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String) {
            fieldWithNullableStringInput(input: $value)
        }
        ''',
        expected_data={'fieldWithNullableStringInput': 'null'},
        expected_errors=[],
        variables={'value': None}
    )


def test_allows_nullable_inputs_to_be_set_to_a_value_in_a_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String) {
            fieldWithNullableStringInput(input: $value)
        }
        ''',
        expected_data={'fieldWithNullableStringInput': '"a"'},
        expected_errors=[],
        variables={'value': 'a'}
    )


def test_allows_nullable_inputs_to_be_set_to_a_value_directly():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithNullableStringInput(input: "a")
        }
        ''',
        expected_data={'fieldWithNullableStringInput': '"a"'},
        expected_errors=[]
    )


def test_allows_non_nullable_inputs_to_be_omitted_given_a_default():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String = "default") {
            fieldWithNonNullableStringInput(input: $value)
        }
        ''',
        expected_data={'fieldWithNonNullableStringInput': '"default"'},
        expected_errors=[]
    )


def test_does_not_allow_non_nullable_inputs_to_be_omitted_in_a_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        ''',
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$value" of required type "String!" was not provided.'
        )
    )


def test_does_not_allow_non_nullable_inputs_to_be_set_to_null_in_a_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        ''',
        variables={'input': None},
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$value" of required type "String!" was not provided.'
        )
    )


def test_allows_non_nullable_inputs_to_be_set_to_a_value_in_a_variable():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        ''',
        expected_data={
            'fieldWithNonNullableStringInput': '"a"'
        },
        expected_errors=[],
        variables={'value': 'a'}
    )


def test_allows_non_nullable_inputs_to_be_set_to_a_value_directly():
    check_execution(
        _SCHEMA,
        '''
        query {
            fieldWithNonNullableStringInput(input: "a")
        }
        ''',
        expected_data={
            'fieldWithNonNullableStringInput': '"a"'
        },
        expected_errors=[]
    )


def test_reports_error_for_missing_non_nullable_inputs():
    with pytest.raises(DocumentValidationError) as exc_info:
        check_execution(_SCHEMA, '{ fieldWithNonNullableStringInput }')

    assert exc_info.value.errors[0][0] == (
        'Field "fieldWithNonNullableStringInput" argument "input" of type '
        'String! is required but not provided'
    )


def test_reports_error_for_missing_non_nullable_inputs_no_validation():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithNonNullableStringInput
        }
        ''',
        {
            'fieldWithNonNullableStringInput': None
        },
        [
            ('Argument "input" of required type "String!" was not provided',
             (23, 54), 'fieldWithNonNullableStringInput')
        ],
        _skip_validation=True,
    )


def test_reports_error_for_array_passed_into_string_input():
    check_execution(
        _SCHEMA,
        '''
        query ($value: String!) {
            fieldWithNonNullableStringInput(input: $value)
        }
        ''',
        variables={'value': [1, 2, 3]},
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$value" got invalid value [1, 2, 3] (String cannot '
            'represent list value "[1, 2, 3]")'
        ),
    )


def test_reports_error_for_non_provided_variables_for_non_nullable_inputs():
    check_execution(
        _SCHEMA,
        '''
        {
            fieldWithNonNullableStringInput(input: $foo)
        }
        ''',
        variables={'value': [1, 2, 3]},
        expected_data={
            'fieldWithNonNullableStringInput': None,
        },
        expected_errors=[
            ('Argument "input" of required type "String!" was provided the '
             'missing variable "$foo"',
             (23, 67), 'fieldWithNonNullableStringInput')
        ],
        # Default rules will would prevent this from executing
        _skip_validation=True
    )


def test_allows_lists_to_be_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String]) {
            list(input: $input)
        }
        ''',
        expected_data={'list': 'null'},
        expected_errors=[],
        variables={'input': None},
    )


def test_allows_lists_to_contain_values():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String]) {
            list(input: $input)
        }
        ''',
        expected_data={'list': '["A"]'},
        expected_errors=[],
        variables={'input': ['A']},
    )


def test_allows_lists_to_contain_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String]) {
            list(input: $input)
        }
        ''',
        expected_data={'list': '["A", null, "B"]'},
        expected_errors=[],
        variables={'input': ['A', None, 'B']},
    )


def test_does_not_allow_non_null_lists_to_be_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String]!) {
            nnList(input: $input)
        }
        ''',
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value null (Expected non-nullable '
            'type [String]! not to be null)'
        ),
        variables={'input': None},
    )


def test_allows_non_null_lists_to_contain_values():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String]!) {
            nnList(input: $input)
        }
        ''',
        expected_data={'nnList': '["A"]'},
        expected_errors=[],
        variables={'input': ['A']},
    )


def test_allows_non_null_lists_to_contain_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String]!) {
            nnList(input: $input)
        }
        ''',
        expected_data={'nnList': '["A", null, "B"]'},
        expected_errors=[],
        variables={'input': ['A', None, 'B']},
    )


def test_does_not_allow_non_null_lists_of_non_nulls_to_be_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String!]!) {
            nnListNN(input: $input)
        }
        ''',
        variables={'input': None},
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value null (Expected non-nullable '
            'type [String!]! not to be null)'
        ),
    )


def test_allows_non_null_lists_of_non_nulls_to_contain_values():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String!]!) {
            nnListNN(input: $input)
        }
        ''',
        variables={'input': ['A']},
        expected_data={'nnListNN': '["A"]'},
        expected_errors=[],
    )


def test_does_not_allow_non_null_lists_of_non_nulls_to_contain_null():
    check_execution(
        _SCHEMA,
        '''
        query ($input: [String!]!) {
            nnListNN(input: $input)
        }
        ''',
        variables={'input': ['A', None, 'B']},
        expected_exc=VariableCoercionError,
        expected_msg=(
            'Variable "$input" got invalid value ["A", null, "B"] (Expected '
            'non-nullable type String! not to be null at value[1])'
        ),
    )


def test_does_not_allow_invalid_types_to_be_used_as_values():
    with pytest.raises(DocumentValidationError) as exc_info:
        check_execution(_SCHEMA, '''
        query ($input: TestType!) {
            fieldWithObjectInput(input: $input)
        }''', variables={'input': ['A', 'B']})

    assert [msg for msg, _ in exc_info.value.errors] == [
        'Variable "$input" must be input type',
        'Variable "$input" of type TestType! used in position expecting type '
        'TestInputObject'
    ]


def test_does_not_allow_unknown_types_to_be_used_as_values():
    with pytest.raises(DocumentValidationError) as exc_info:
        check_execution(_SCHEMA, '''
        query ($input: UnknownType!) {
          fieldWithObjectInput(input: $input)
        }''', variables={'input': 'whoknows'})

    assert [msg for msg, _ in exc_info.value.errors] == [
        'Unknown type "UnknownType"',
        'Variable "$input" must be input type',
        'Variable "$input" of type UnknownType! used in position expecting '
        'type TestInputObject'
    ]


def test_argument_default_values_when_no_argument_provided():
    check_execution(
        _SCHEMA,
        '{ fieldWithDefaultArgumentValue }',
        expected_data={
            'fieldWithDefaultArgumentValue': '"Hello World"',
        },
        expected_errors=[]
    )


def test_argument_default_values_when_omitted_variable_provided():
    check_execution(
        _SCHEMA,
        '''
        query ($optional: String) {
            fieldWithDefaultArgumentValue(input: $optional)
        }
        ''',
        expected_data={
            'fieldWithDefaultArgumentValue': '"Hello World"',
        },
        expected_errors=[]
    )


def test_argument_default_value_when_argument_cannot_be_coerced():
    with pytest.raises(DocumentValidationError) as exc_info:
        check_execution(
            _SCHEMA,
            '{ fieldWithDefaultArgumentValue(input: WRONG_TYPE) }',
        )

    assert [msg for msg, _ in exc_info.value.errors] == [
        'Expected type String, found WRONG_TYPE',
    ]