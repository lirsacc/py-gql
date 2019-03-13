# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import VariablesAreInputTypesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_input_types_are_valid(schema):
    run_test(
        VariablesAreInputTypesChecker,
        schema,
        """
        query Foo($a: String, $b: [Boolean!]!, $c: ComplexInput) {
            field(a: $a, b: $b, c: $c)
        }
        """,
    )


def test_output_types_are_invalid(schema):
    run_test(
        VariablesAreInputTypesChecker,
        schema,
        """
        query Foo($a: Dog, $b: [[CatOrDog!]]!, $c: Pet) {
            field(a: $a, b: $b, c: $c)
        }
        """,
        [
            'Variable "$a" must be input type',
            'Variable "$b" must be input type',
            'Variable "$c" must be input type',
        ],
    )


def test_unknown_types_are_invalid(schema):
    run_test(
        VariablesAreInputTypesChecker,
        schema,
        """
        query Foo($a: Bar) {
            field(a: $a)
        }
        """,
        ['Variable "$a" must be input type'],
    )
