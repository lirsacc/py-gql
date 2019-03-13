# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import UniqueDirectivesPerLocationChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_no_directives(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field
        }
        """,
    )


def test_unique_directives_in_different_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directiveA {
            field @directiveB
        }
        """,
    )


def test_unique_directives_in_same_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directiveA @directiveB {
            field @directiveA @directiveB
        }
        """,
    )


def test_same_directives_in_different_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directiveA {
            field @directiveA
        }
        """,
    )


def test_same_directives_in_similar_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @directive
            field @directive
        }
        """,
    )


def test_duplicate_directives_in_one_location(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @directive @directive
        }
        """,
        ['Duplicate directive "@directive"'],
        [[(45, 55)]],
    )


def test_many_duplicate_directives_in_one_location(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @directive @directive @directive
        }
        """,
        [
            'Duplicate directive "@directive"',
            'Duplicate directive "@directive"',
        ],
        [[(45, 55)], [(56, 66)]],
    )


def test_different_duplicate_directives_in_one_location(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type {
            field @directiveA @directiveB @directiveA @directiveB
        }
        """,
        [
            'Duplicate directive "@directiveA"',
            'Duplicate directive "@directiveB"',
        ],
        [[(58, 69)], [(70, 81)]],
    )


def test_duplicate_directives_in_many_locations(schema):
    run_test(
        UniqueDirectivesPerLocationChecker,
        schema,
        """
        fragment Test on Type @directive @directive {
            field @directive @directive
        }
        """,
        [
            'Duplicate directive "@directive"',
            'Duplicate directive "@directive"',
        ],
        [[(33, 43)], [(67, 77)]],
    )
