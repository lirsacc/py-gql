# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import UniqueArgumentNamesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_no_arguments_on_field(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field
        }
        """,
    )


def test_no_arguments_on_directive(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field @directive
        }
        """,
    )


def test_argument_on_field(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field(arg: "value")
        }
        """,
    )


def test_argument_on_directive(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field @directive(arg: "value")
        }
        """,
    )


def test_same_argument_on_two_fields(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            one: field(arg: "value")
            two: field(arg: "value")
        }
        """,
    )


def test_same_argument_on_field_and_directive(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field(arg: "value") @directive(arg: "value")
        }
        """,
    )


def test_same_argument_on_two_directives(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field @directive1(arg: "value") @directive2(arg: "value")
        }
        """,
    )


def test_multiple_field_arguments(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field(arg1: "value", arg2: "value", arg3: "value")
        }
        """,
    )


def test_multiple_directive_arguments(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field @directive(arg1: "value", arg2: "value", arg3: "value")
        }
        """,
    )


def test_duplicate_field_arguments(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field(arg1: "value", arg1: "value")
        }
        """,
        ['Duplicate argument "arg1"'],
        [[(27, 40)]],
    )


def test_many_duplicate_field_arguments(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field(arg1: "value", arg1: "value", arg1: "value")
        }
        """,
        ['Duplicate argument "arg1"', 'Duplicate argument "arg1"'],
        [[(27, 40)], [(42, 55)]],
    )


def test_duplicate_directive_arguments(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field @directive(arg1: "value", arg1: "value")
        }
        """,
        ['Duplicate argument "arg1"'],
    )


def test_many_duplicate_directive_arguments(schema):
    run_test(
        UniqueArgumentNamesChecker,
        schema,
        """
        {
            field @directive(arg1: "value", arg1: "value", arg1: "value")
        }
        """,
        ['Duplicate argument "arg1"', 'Duplicate argument "arg1"'],
    )
