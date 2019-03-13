# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import UniqueInputFieldNamesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_input_object_with_fields(schema):
    run_test(
        UniqueInputFieldNamesChecker,
        schema,
        """
        {
            field(arg: { f: true })
        }
        """,
    )


def test_same_input_object_within_two_args(schema):
    run_test(
        UniqueInputFieldNamesChecker,
        schema,
        """
        {
            field(arg1: { f: true }, arg2: { f: true })
        }
        """,
    )


def test_multiple_input_object_fields(schema):
    run_test(
        UniqueInputFieldNamesChecker,
        schema,
        """
        {
            field(arg: { f1: "value", f2: "value", f3: "value" })
        }
        """,
    )


def test_allows_for_nested_input_objects_with_similar_fields(schema):
    run_test(
        UniqueInputFieldNamesChecker,
        schema,
        """
        {
            field(arg: {
                deep: {
                    deep: {
                        id: 1
                    }
                    id: 1
                }
                id: 1
            })
        }
        """,
    )


def test_duplicate_input_object_fields(schema):
    run_test(
        UniqueInputFieldNamesChecker,
        schema,
        """
        {
            field(arg: { f1: "value", f1: "value" })
        }
        """,
        ["There can be only one input field named f1."],
        [[(32, 43)]],
    )


def test_many_duplicate_input_object_fields(schema):
    run_test(
        UniqueInputFieldNamesChecker,
        schema,
        """
        {
            field(arg: { f1: "value", f1: "value", f1: "value" })
        }
        """,
        [
            "There can be only one input field named f1.",
            "There can be only one input field named f1.",
        ],
        [[(32, 43)], [(45, 56)]],
    )
