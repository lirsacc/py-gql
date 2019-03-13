# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

from py_gql.validation.rules import NoUndefinedVariablesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_all_variables_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            field(a: $a, b: $b, c: $c)
        }
        """,
    )


def test_all_variables_deeply_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
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


def test_all_variables_deeply_in_inline_fragments_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
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


def test_all_variables_in_fragments_deeply_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
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


def test_variable_within_single_fragment_defined_in_multiple_operations(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($a: String) {
            ...FragA
        }
        query Bar($a: String) {
            ...FragA
        }
        fragment FragA on Type {
            field(a: $a)
        }
        """,
    )


def test_variable_within_fragments_defined_in_operations(schema):
    run_test(
        NoUndefinedVariablesChecker,
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


def test_variable_within_recursive_fragment_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
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


def test_variable_not_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String, $c: String) {
            field(a: $a, b: $b, c: $c, d: $d)
        }
        """,
        ['Variable "$d" is not defined on "Foo" operation'],
        [[(82, 84)]],
    )


def test_variable_not_defined_by_unnamed_query(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        {
            field(a: $a)
        }
        """,
        ['Variable "$a" is not defined on anonymous operation'],
        [[(15, 17)]],
    )


def test_multiple_variables_not_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($b: String) {
            field(a: $a, b: $b, c: $c)
        }
        """,
        [
            'Variable "$a" is not defined on "Foo" operation',
            'Variable "$c" is not defined on "Foo" operation',
        ],
    )


def test_variable_in_fragment_not_defined_by_unnamed_query(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        {
            ...FragA
        }
        fragment FragA on Type {
            field(a: $a)
        }
        """,
        [
            'Variable "$a" from fragment "FragA" is not defined on anonymous'
            " operation"
        ],
    )


def test_variable_in_fragment_not_defined_by_operation(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($a: String, $b: String) {
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
        [
            'Variable "$c" from fragment "FragC" is not defined on "Foo" operation'
        ],
    )


def test_multiple_variables_in_fragments_not_defined(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($b: String) {
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
        [
            'Variable "$a" from fragment "FragA" is not defined on "Foo" operation',
            'Variable "$c" from fragment "FragC" is not defined on "Foo" operation',
        ],
    )


def test_single_variable_in_fragment_not_defined_by_multiple_operations(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($b: String) {
            ...FragAB
        }
        query Bar($a: String) {
            ...FragAB
        }
        fragment FragAB on Type {
            field(a: $a, b: $b)
        }
        """,
        [
            'Variable "$a" from fragment "FragAB" is not defined on "Foo" '
            "operation",
            'Variable "$b" from fragment "FragAB" is not defined on "Bar" '
            "operation",
        ],
    )


def test_variables_in_fragment_not_defined_by_multiple_operations(schema):
    run_test(
        NoUndefinedVariablesChecker,
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
        [
            'Variable "$a" from fragment "FragA" is not defined on "Foo" operation',
            'Variable "$b" from fragment "FragB" is not defined on "Bar" operation',
        ],
    )


def test_variable_in_fragment_used_by_other_operation(schema):
    run_test(
        NoUndefinedVariablesChecker,
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
        [
            'Variable "$a" from fragment "FragA" is not defined on "Foo" operation',
            'Variable "$b" from fragment "FragB" is not defined on "Bar" operation',
        ],
    )


def test_multiple_undefined_variables_produce_multiple_errors(schema):
    run_test(
        NoUndefinedVariablesChecker,
        schema,
        """
        query Foo($b: String) {
            ...FragAB
        }
        query Bar($a: String) {
            ...FragAB
        }
        fragment FragAB on Type {
            field1(a: $a, b: $b)
            ...FragC
            field3(a: $a, b: $b)
        }
        fragment FragC on Type {
            field2(c: $c)
        }
        """,
        [
            'Variable "$a" from fragment "FragAB" is not defined on "Foo" operation',
            'Variable "$c" from fragment "FragC" is not defined on "Foo" operation',
            'Variable "$b" from fragment "FragAB" is not defined on "Bar" operation',
            'Variable "$c" from fragment "FragC" is not defined on "Bar" operation',
        ],
    )
