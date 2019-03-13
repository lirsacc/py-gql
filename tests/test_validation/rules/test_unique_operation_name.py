# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import UniqueOperationNameChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_no_operations(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """fragment fragA on Type {
            field
        }
        """,
    )


def test_one_anon_operation(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """{
            field
        }
        """,
    )


def test_one_named_operation(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """query {
            field
        }
        """,
    )


def test_multiple_operations(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """
        query Foo {
            field
        }

        query Bar {
            field
        }
        """,
    )


def test_multiple_operations_of_different_types(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """
        query Foo {
            field
        }

        mutation Bar {
            field
        }

        subscription Baz {
            field
        }
        """,
    )


def test_fragment_and_operation_named_the_same(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """
        query Foo {
            ...Foo
        }
        fragment Foo on Type {
            field
        }
        """,
    )


def test_multiple_operations_of_same_name(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """
        query Foo {
            fieldA
        }

        query Foo {
            fieldB
        }
        """,
        ['Duplicate operation "Foo".'],
    )


def test_multiple_ops_of_same_name_of_different_types_mutation(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """
        query Foo {
            fieldA
        }

        mutation Foo {
            fieldB
        }
        """,
        ['Duplicate operation "Foo".'],
    )


def test_multiple_ops_of_same_name_of_different_types_subscription(schema):
    run_test(
        UniqueOperationNameChecker,
        schema,
        """
        query Foo {
            fieldA
        }

        subscription Foo {
            fieldB
        }
        """,
        ['Duplicate operation "Foo".'],
    )
