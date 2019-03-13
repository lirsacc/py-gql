# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import UniqueVariableNamesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_unique_variable_names(schema):
    run_test(
        UniqueVariableNamesChecker,
        schema,
        """
            query A($x: Int, $y: String) { __typename }
            query B($x: String, $y: Int) { __typename }
        """,
    )


def test_duplicate_variable_names(schema):
    run_test(
        UniqueVariableNamesChecker,
        schema,
        """
            query A($x: Int, $x: Int, $x: String) { __typename }
            query B($x: String, $x: Int) { __typename }
            query C($x: Int, $x: Int) { __typename }
        """,
        [
            'Duplicate variable "$x"',
            'Duplicate variable "$x"',
            'Duplicate variable "$x"',
            'Duplicate variable "$x"',
        ],
        [[(17, 24)], [(26, 36)], [(73, 80)], [(114, 121)]],
    )
