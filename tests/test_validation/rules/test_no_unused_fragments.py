# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import NoUnusedFragmentsChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_all_fragment_names_are_used(schema):
    run_test(
        NoUnusedFragmentsChecker,
        schema,
        """
        {
            human(id: 4) {
                ...HumanFields1
                ... on Human {
                    ...HumanFields2
                }
            }
        }
        fragment HumanFields1 on Human {
            name
            ...HumanFields3
        }
        fragment HumanFields2 on Human {
            name
        }
        fragment HumanFields3 on Human {
            name
        }
        """,
    )


def test_all_fragment_names_are_used_by_multiple_operations(schema):
    run_test(
        NoUnusedFragmentsChecker,
        schema,
        """
        query Foo {
            human(id: 4) {
                ...HumanFields1
            }
        }
        query Bar {
            human(id: 4) {
                ...HumanFields2
            }
        }
        fragment HumanFields1 on Human {
            name
            ...HumanFields3
        }
        fragment HumanFields2 on Human {
            name
        }
        fragment HumanFields3 on Human {
            name
        }
        """,
    )


def test_contains_unknown_fragments(schema):
    run_test(
        NoUnusedFragmentsChecker,
        schema,
        """
        query Foo {
            human(id: 4) {
                ...HumanFields1
            }
        }
        query Bar {
            human(id: 4) {
                ...HumanFields2
            }
        }
        fragment HumanFields1 on Human {
            name
            ...HumanFields3
        }
        fragment HumanFields2 on Human {
            name
        }
        fragment HumanFields3 on Human {
            name
        }
        fragment Unused1 on Human {
            name
        }
        fragment Unused2 on Human {
            name
        }
        """,
        ['Unused fragment(s) "Unused1", "Unused2"'],
    )


# Different from the reference test as we leave the cycle checks to
# the corresponding rule (NoFragmentCyclesChecker) while this rule
# considers used cyclic fragments as correct
def test_contains_unknown_fragments_with_ref_cycle(schema):
    run_test(
        NoUnusedFragmentsChecker,
        schema,
        """
        query Foo {
            human(id: 4) {
                ...HumanFields1
            }
        }
        query Bar {
            human(id: 4) {
                ...HumanFields2
            }
        }
        fragment HumanFields1 on Human {
            name
            ...HumanFields3
        }
        fragment HumanFields2 on Human {
            name
        }
        fragment HumanFields3 on Human {
            name
        }
        fragment Unused1 on Human {
            name
            ...Unused2
        }
        fragment Unused2 on Human {
            name
            ...Unused1
        }
        """,
    )


def test_contains_unknown_and_undef_fragments(schema):
    run_test(
        NoUnusedFragmentsChecker,
        schema,
        """
        query Foo {
            human(id: 4) {
                ...bar
            }
        }
        fragment foo on Human {
            name
        }
        """,
        ['Unused fragment(s) "foo"'],
    )
