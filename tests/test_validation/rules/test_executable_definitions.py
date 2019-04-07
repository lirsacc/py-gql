# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import ExecutableDefinitionsChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_only_operation(schema):
    run_test(
        ExecutableDefinitionsChecker,
        schema,
        """
        query Foo {
            dog {
                name
            }
        }
        """,
    )


def test_operation_and_fragment(schema):
    run_test(
        ExecutableDefinitionsChecker,
        schema,
        """
        query Foo {
            dog {
                name
                ...Frag
            }
        }

        fragment Frag on Dog {
            name
        }
        """,
    )


def test_type_definition(schema):
    run_test(
        ExecutableDefinitionsChecker,
        schema,
        """
        query Foo {
            dog {
                name
            }
        }

        type Cow {
            name: String
        }

        extend type Dog {
            color: String
        }
        """,
        [
            "The Cow definition is not executable.",
            "The Dog definition is not executable.",
        ],
    )


def test_schema_definition(schema):
    run_test(
        ExecutableDefinitionsChecker,
        schema,
        """
        schema {
            query: Query
        }

        type Query {
            test: String
        }
        """,
        [
            "The schema definition is not executable.",
            "The Query definition is not executable.",
        ],
    )
