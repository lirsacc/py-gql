# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are applicable but
# they conserved as comments for reference.


from py_gql.validation.rules import KnownFragmentNamesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_known_fragment_names_are_valid(schema):
    run_test(
        KnownFragmentNamesChecker,
        schema,
        """
        {
            human(id: 4) {
            ...HumanFields1
            ... on Human {
                ...HumanFields2
            }
            ... {
                name
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


def test_unknown_fragment_names_are_invalid(schema):
    run_test(
        KnownFragmentNamesChecker,
        schema,
        """
        {
            human(id: 4) {
            ...UnknownFragment1
            ... on Human {
                ...UnknownFragment2
            }
            }
        }
        fragment HumanFields on Human {
            name
            ...UnknownFragment3
        }
        """,
        [
            'Unknown fragment "UnknownFragment1"',
            'Unknown fragment "UnknownFragment2"',
            'Unknown fragment "UnknownFragment3"',
        ],
    )
