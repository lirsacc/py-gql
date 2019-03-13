# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import NoFragmentCyclesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_single_reference_is_valid(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB }
        fragment fragB on Dog { name }
        """,
    )


def test_spreading_twice_is_not_circular(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB, ...fragB }
        fragment fragB on Dog { name }
        """,
    )


def test_spreading_twice_indirectly_is_not_circular(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB, ...fragC }
        fragment fragB on Dog { ...fragC }
        fragment fragC on Dog { name }
        """,
    )


def test_double_spread_within_abstract_types(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment nameFragment on Pet {
            ... on Dog { name }
            ... on Cat { name }
        }

        fragment spreadsInAnon on Pet {
            ... on Dog { ...nameFragment }
            ... on Cat { ...nameFragment }
        }
        """,
    )


def test_does_not_false_positive_on_unknown_fragment(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment nameFragment on Pet {
            ...UnknownFragment
        }
        """,
    )


def test_spreading_recursively_within_field_fails(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Human { relatives { ...fragA } },
        """,
        ['Cannot spread fragment "fragA" withing itself'],
    )


def test_no_spreading_itself_directly(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragA }
        """,
        ['Cannot spread fragment "fragA" withing itself'],
    )


def test_no_spreading_itself_directly_within_inline_fragment(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Pet {
            ... on Dog {
                ...fragA
            }
        }
        """,
        ['Cannot spread fragment "fragA" withing itself'],
    )


def test_no_spreading_itself_indirectly(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB }
        fragment fragB on Dog { ...fragA }
        """,
        ['Cannot spread fragment "fragA" withing itself (via: fragB)'],
    )


def test_no_spreading_itself_indirectly_reports_opposite_order(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragB on Dog { ...fragA }
        fragment fragA on Dog { ...fragB }
        """,
        ['Cannot spread fragment "fragB" withing itself (via: fragA)'],
    )


def test_no_spreading_itself_indirectly_within_inline_fragment(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Pet {
            ... on Dog {
                ...fragB
            }
        }
        fragment fragB on Pet {
            ... on Dog {
                ...fragA
            }
        }
        """,
        ['Cannot spread fragment "fragA" withing itself (via: fragB)'],
    )


def test_no_spreading_itself_deeply(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB }
        fragment fragB on Dog { ...fragC }
        fragment fragC on Dog { ...fragO }
        fragment fragX on Dog { ...fragY }
        fragment fragY on Dog { ...fragZ }
        fragment fragZ on Dog { ...fragO }
        fragment fragO on Dog { ...fragP }
        fragment fragP on Dog { ...fragA, ...fragX }
        """,
        [
            'Cannot spread fragment "fragA" withing itself (via: fragB > fragC '
            "> fragO > fragP)",
            # Same priority but different iteration order from ref implementation.
            # 'Cannot spread fragment "fragO" withing itself (via: fragP > fragX '
            # '> fragY > fragZ)',
            'Cannot spread fragment "fragX" withing itself (via: fragY > fragZ '
            "> fragO > fragP)",
        ],
    )


def test_no_spreading_itself_deeply_two_paths(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB, ...fragC }
        fragment fragB on Dog { ...fragA }
        fragment fragC on Dog { ...fragA }
        """,
        [
            'Cannot spread fragment "fragA" withing itself (via: fragB)',
            # 'Cannot spread fragment "fragA" withing itself (via: fragC)',
        ],
    )


def test_no_spreading_itself_deeply_two_paths_alt_traverse_order(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragC }
        fragment fragB on Dog { ...fragC }
        fragment fragC on Dog { ...fragA, ...fragB }
        """,
        [
            'Cannot spread fragment "fragA" withing itself (via: fragC)',
            'Cannot spread fragment "fragB" withing itself (via: fragC)',
        ],
    )


def test_no_spreading_itself_deeply_and_immediately(schema):
    run_test(
        NoFragmentCyclesChecker,
        schema,
        """
        fragment fragA on Dog { ...fragB }
        fragment fragB on Dog { ...fragB, ...fragC }
        fragment fragC on Dog { ...fragA, ...fragB }
        """,
        [
            'Cannot spread fragment "fragB" withing itself',
            'Cannot spread fragment "fragA" withing itself (via: fragB > fragC)',
            # 'Cannot spread fragment "fragB" withing itself (via: fragC)',
        ],
    )
