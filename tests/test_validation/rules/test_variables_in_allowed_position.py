# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import VariablesInAllowedPositionChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_boolean_to_boolean(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($booleanArg: Boolean)
        {
            complicatedArgs {
                booleanArgField(booleanArg: $booleanArg)
            }
        }
        """,
    )


def test_boolean_to_boolean_within_fragment_0(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        fragment booleanArgFrag on ComplicatedArgs {
            booleanArgField(booleanArg: $booleanArg)
        }

        query Query($booleanArg: Boolean) {
            complicatedArgs {
                ...booleanArgFrag
            }
        }
        """,
    )


def test_boolean_to_boolean_within_fragment_1(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($booleanArg: Boolean) {
            complicatedArgs {
                ...booleanArgFrag
            }
        }

        fragment booleanArgFrag on ComplicatedArgs {
            booleanArgField(booleanArg: $booleanArg)
        }
        """,
    )


def test_required_boolean_to_boolean(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($nonNullBooleanArg: Boolean!) {
            complicatedArgs {
                booleanArgField(booleanArg: $nonNullBooleanArg)
            }
        }
        """,
    )


def test_required_boolean_to_boolean_within_fragment(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        fragment booleanArgFrag on ComplicatedArgs {
            booleanArgField(booleanArg: $nonNullBooleanArg)
        }

        query Query($nonNullBooleanArg: Boolean!) {
            complicatedArgs {
                ...booleanArgFrag
            }
        }
        """,
    )


def test_int_to_required_int_with_default(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($intArg: Int = 1)
        {
            complicatedArgs {
                nonNullIntArgField(nonNullIntArg: $intArg)
            }
        }
        """,
    )


def test_list_of_string_to_list_of_string(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringListVar: [String]) {
            complicatedArgs {
                stringListArgField(stringListArg: $stringListVar)
            }
        }
        """,
    )


def test_list_of_required_string_to_list_of_string(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringListVar: [String!]) {
            complicatedArgs {
                stringListArgField(stringListArg: $stringListVar)
            }
        }
        """,
    )


def test_string_to_list_of_string_in_field(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringVar: String) {
            complicatedArgs {
                stringListArgField(stringListArg: [$stringVar])
            }
        }
        """,
    )


def test_required_string_to_list_of_string(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringVar: String!) {
            complicatedArgs {
                stringListArgField(stringListArg: [$stringVar])
            }
        }
        """,
    )


def test_complex_input_to_complex_input(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($complexVar: ComplexInput) {
            complicatedArgs {
                complexArgField(complexArg: $complexVar)
            }
        }
        """,
    )


def test_complex_input_field_to_complex_input_field_0(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($boolVar: Boolean = false) {
            complicatedArgs {
                complexArgField(complexArg: {requiredField: $boolVar})
            }
        }
        """,
    )


def test_complex_input_field_to_complex_input_field_1(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($boolVar: Boolean = false) {
            complicatedArgs {
                complexArgField(complexArg: {requiredArg: $boolVar})
            }
        }
        """,
    )


def test_req_boolean_to_req_boolean_in_directive(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($boolVar: Boolean!) {
            dog @include(if: $boolVar)
        }
        """,
    )


def test_boolean_to_req_boolean_in_directive_with_default(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($boolVar: Boolean = false) {
            dog @include(if: $boolVar)
        }
        """,
    )


def test_int_to_required_int(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($intArg: Int) {
            complicatedArgs {
                nonNullIntArgField(nonNullIntArg: $intArg)
            }
        }
        """,
        ['Variable "$intArg" of type Int used in position expecting type Int!'],
        [(92, 99)],
    )


def test_int_to_required_int_within_fragment(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        fragment nonNullIntArgFieldFrag on ComplicatedArgs {
            nonNullIntArgField(nonNullIntArg: $intArg)
        }

        query Query($intArg: Int) {
            complicatedArgs {
                ...nonNullIntArgFieldFrag
            }
        }
        """,
        ['Variable "$intArg" of type Int used in position expecting type Int!'],
        [(91, 98)],
    )


def test_int_to_required_int_within_nested_fragment(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        fragment outerFrag on ComplicatedArgs {
            ...nonNullIntArgFieldFrag
        }

        fragment nonNullIntArgFieldFrag on ComplicatedArgs {
            nonNullIntArgField(nonNullIntArg: $intArg)
        }

        query Query($intArg: Int) {
            complicatedArgs {
                ...outerFrag
            }
        }
        """,
        ['Variable "$intArg" of type Int used in position expecting type Int!'],
        [(164, 171)],
    )


def test_string_over_boolean(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringVar: String) {
            complicatedArgs {
                booleanArgField(booleanArg: $stringVar)
            }
        }
        """,
        [
            'Variable "$stringVar" of type String used in position expecting '
            "type Boolean"
        ],
    )


def test_string_to_list_of_string(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringVar: String) {
            complicatedArgs {
                stringListArgField(stringListArg: $stringVar)
            }
        }
        """,
        [
            'Variable "$stringVar" of type String used in position expecting '
            "type [String]"
        ],
    )


def test_boolean_to_required_boolean_in_directive(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($boolVar: Boolean) {
            dog @include(if: $boolVar)
        }
        """,
        [
            'Variable "$boolVar" of type Boolean used in position expecting '
            "type Boolean!"
        ],
    )


def test_string_to_required_boolean_in_directive(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringVar: String) {
            dog @include(if: $stringVar)
        }
        """,
        [
            'Variable "$stringVar" of type String used in position expecting '
            "type Boolean!"
        ],
    )


def test_list_of_string_to_list_of_required_string(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($stringListVar: [String]) {
            complicatedArgs {
                stringListNonNullArgField(stringListNonNullArg: $stringListVar)
            }
        }
        """,
        [
            'Variable "$stringListVar" of type [String] used in position '
            "expecting type [String!]"
        ],
    )


def test_int_to_non_null_int_fails_when_variable_provides_null_default(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($intVar: Int = null) {
            complicatedArgs {
                nonNullIntArgField(nonNullIntArg: $intVar)
            }
        }
        """,
        ['Variable "$intVar" of type Int used in position expecting type Int!'],
        [(99, 106)],
    )


def test_int_to_non_null_int_ok_when_variable_provides_non_null_default(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($intVar: Int = 1) {
            complicatedArgs {
                nonNullIntArgField(nonNullIntArg: $intVar)
            }
        }
        """,
    )


def test_int_to_non_null_int_ok_when_optional_argument_provides_default(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($intVar: Int) {
            complicatedArgs {
                nonNullFieldWithDefault(nonNullIntArg: $intVar)
            }
        }
        """,
    )


def test_bool_to_non_null_bool_in_directive_with_default_with_option(schema):
    run_test(
        VariablesInAllowedPositionChecker,
        schema,
        """
        query Query($boolVar: Boolean = false) {
            dog @include(if: $boolVar)
        }
        """,
    )
