# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import LoneAnonymousOperationChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_no_operations(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        fragment fragA on Type {
            field
        }""",
    )


def test_one_anon_operation(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        {
            field
        }""",
    )


def test_multiple_named_operations(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        query Foo {
            field
        }

        query Bar {
            field
        }""",
    )


def test_anon_operation_with_fragment(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        {
            ...Foo
        }
        fragment Foo on Type {
            field
        }""",
    )


def test_multiple_anon_operations(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        {
            fieldA
        }
        {
            fieldB
        }
        """,
        ["The anonymous operation must be the only defined operation."],
    )


def test_anon_operation_with_a_mutation(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        {
            fieldA
        }
        mutation Foo {
            fieldB
        }
        """,
        ["The anonymous operation must be the only defined operation."],
    )


def test_anon_operation_with_a_subscription(schema):
    run_test(
        LoneAnonymousOperationChecker,
        schema,
        """
        {
            fieldA
        }
        subscription Foo {
            fieldB
        }
        """,
        ["The anonymous operation must be the only defined operation."],
    )
