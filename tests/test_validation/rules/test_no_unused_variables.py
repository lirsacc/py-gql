# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import NoUnusedVariablesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_uses_all_variables(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query ($a: String, $b: String, $c: String) {
            field(a: $a, b: $b, c: $c)
        }
        """,
    )


def test_uses_all_variables_deeply(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            field(a: $a) {
                field(b: $b) {
                field(c: $c)
                }
            }
        }
        """,
    )


def test_uses_all_variables_deeply_in_inline_fragments(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            ... on Type {
                field(a: $a) {
                    field(b: $b) {
                        ... on Type {
                            field(c: $c)
                        }
                    }
                }
            }
        }
        """,
    )


def test_uses_all_variables_in_fragments(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            ...FragA
        }
        fragment FragA on Type {
            field(a: $a) {
                ...FragB
            }
        }
        fragment FragB on Type {
            field(b: $b) {
                ...FragC
            }
        }
        fragment FragC on Type {
            field(c: $c)
        }
        """,
    )


def test_variable_used_by_fragment_in_multiple_operations(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String) {
            ...FragA
        }
        query Bar($b: String) {
            ...FragB
        }
        fragment FragA on Type {
            field(a: $a)
        }
        fragment FragB on Type {
            field(b: $b)
        }
        """,
    )


def test_variable_used_by_recursive_fragment(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String) {
            ...FragA
        }
        fragment FragA on Type {
            field(a: $a) {
                ...FragA
            }
        }
        """,
    )


def test_variable_not_used(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query ($a: String, $b: String, $c: String) {
            field(a: $a, b: $b)
        }
        """,
        ['Unused variable "$c"'],
        [[(31, 41)]],
    )


def test_multiple_variables_not_used(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            field(b: $b)
        }
        """,
        ['Unused variable "$a"', 'Unused variable "$c"'],
        [[(10, 20)], [(34, 44)]],
    )


def test_variable_not_used_in_fragments(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            ...FragA
        }
        fragment FragA on Type {
            field(a: $a) {
                ...FragB
            }
        }
        fragment FragB on Type {
            field(b: $b) {
                ...FragC
            }
        }
        fragment FragC on Type {
            field
        }
        """,
        ['Unused variable "$c"'],
        [[(34, 44)]],
    )


def test_multiple_variables_not_used_in_fragments(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            ...FragA
        }
        fragment FragA on Type {
            field {
                ...FragB
            }
        }
        fragment FragB on Type {
            field(b: $b) {
                ...FragC
            }
        }
        fragment FragC on Type {
            field
        }
        """,
        ['Unused variable "$a"', 'Unused variable "$c"'],
    )


def test_variable_not_used_by_unreferenced_fragment(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($b: String) {
            ...FragA
        }
        fragment FragA on Type {
            field(a: $a)
        }
        fragment FragB on Type {
            field(b: $b)
        }
        """,
        ['Unused variable "$b"'],
    )


def test_variable_not_used_by_fragment_used_by_other_operation(schema):
    run_test(
        NoUnusedVariablesChecker,
        schema,
        """
        query Foo($b: String) {
            ...FragA
        }
        query Bar($a: String) {
            ...FragB
        }
        fragment FragA on Type {
            field(a: $a)
        }
        fragment FragB on Type {
            field(b: $b)
        }
        """,
        ['Unused variable "$b"', 'Unused variable "$a"'],
    )
