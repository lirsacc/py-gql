# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import VariablesDefaultValueAllowedChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_variables_with_no_default_values(schema):
    run_test(
        VariablesDefaultValueAllowedChecker,
        schema,
        """
    query NullableValues($a: Int, $b: String, $c: ComplexInput) {
        dog { name }
    }
    """,
    )


def test_required_variables_without_default_values(schema):
    run_test(
        VariablesDefaultValueAllowedChecker,
        schema,
        """
    query RequiredValues($a: Int!, $b: String!) {
        dog { name }
    }
    """,
    )


def test_variables_with_valid_default_values(schema):
    run_test(
        VariablesDefaultValueAllowedChecker,
        schema,
        """
    query WithDefaultValues(
        $a: Int = 1,
        $b: String = "ok",
        $c: ComplexInput = { requiredField: true, intField: 3 }
    ) {
        dog { name }
    }
    """,
    )


def test_variables_with_valid_default_null_values(schema):
    run_test(
        VariablesDefaultValueAllowedChecker,
        schema,
        """
    query WithDefaultValues(
        $a: Int = null,
        $b: String = null,
        $c: ComplexInput = { requiredField: true, intField: null }
    ) {
        dog { name }
    }
    """,
    )


def test_no_required_variables_with_default_values(schema):
    run_test(
        VariablesDefaultValueAllowedChecker,
        schema,
        """
    query UnreachableDefaultValues($a: Int! = 3, $b: String! = "default") {
        dog { name }
    }
    """,
        [
            'Variable "$a" of type Int! is required and will not use '
            "the default value",
            'Variable "$b" of type String! is required and will not use '
            "the default value",
        ],
        [(36, 48), (50, 73)],
    )


def test_variables_with_invalid_default_null_values(schema):
    run_test(
        VariablesDefaultValueAllowedChecker,
        schema,
        """
    query WithDefaultValues($a: Int! = null, $b: String! = null) {
        dog { name }
    }
    """,
        [
            'Variable "$a" of type Int! is required and will not use '
            "the default value",
            'Variable "$b" of type String! is required and will not use '
            "the default value",
        ],
    )
