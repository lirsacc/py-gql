# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import UniqueFragmentNamesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_no_fragments(schema):
    run_test(
        UniqueFragmentNamesChecker,
        schema,
        """
        {
            field
        }
        """,
    )


def test_one_fragment(schema):
    run_test(
        UniqueFragmentNamesChecker,
        schema,
        """
        {
            ...fragA
        }

        fragment fragA on Type {
            field
        }
        """,
    )


def test_many_fragments(schema):
    run_test(
        UniqueFragmentNamesChecker,
        schema,
        """
        {
            ...fragA
            ...fragB
            ...fragC
        }
        fragment fragA on Type {
            fieldA
        }
        fragment fragB on Type {
            fieldB
        }
        fragment fragC on Type {
            fieldC
        }
        """,
    )


def test_inline_fragments_are_always_unique(schema):
    run_test(
        UniqueFragmentNamesChecker,
        schema,
        """
        {
            ...on Type {
                fieldA
            }
            ...on Type {
                fieldB
            }
        }
        """,
    )


def test_fragment_and_operation_named_the_same(schema):
    run_test(
        UniqueFragmentNamesChecker,
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


def test_fragments_named_the_same(schema):
    run_test(
        UniqueFragmentNamesChecker,
        schema,
        """
        {
            ...fragA
        }
        fragment fragA on Type {
            fieldA
        }
        fragment fragA on Type {
            fieldB
        }
        """,
        ['There can only be one fragment named "fragA"'],
    )


def test_fragments_named_the_same_without_being_referenced(schema):
    run_test(
        UniqueFragmentNamesChecker,
        schema,
        """
        fragment fragA on Type {
            fieldA
        }
        fragment fragA on Type {
            fieldB
        }
        """,
        ['There can only be one fragment named "fragA"'],
    )
