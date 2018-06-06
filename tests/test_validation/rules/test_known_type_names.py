# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation import KnownTypeNamesChecker
from .._test_utils import assert_checker_validation_result as run_test


def test_known_type_names_are_valid(schema):
    run_test(KnownTypeNamesChecker, schema, '''
    query Foo($var: String, $required: [String!]!) {
        user(id: 4) {
            pets { ... on Pet { name }, ...PetFields, ... { name } }
        }
    }
    fragment PetFields on Pet {
        name
    }
    ''')


def test_unknown_type_names_are_invalid(schema):
    run_test(KnownTypeNamesChecker, schema, '''
    query Foo($var: JumbledUpLetters) {
        user(id: 4) {
            name
            pets { ... on Badger { name }, ...PetFields }
        }
    }
    fragment PetFields on Peettt {
        name
    }
    ''', [
        'Unknown type "JumbledUpLetters"',
        # 'Unknown type "Badger"',
        # 'Unknown type "Peettt"',
    ])


def test_ignores_type_definitions(schema):
    run_test(KnownTypeNamesChecker, schema, '''
    type NotInTheSchema {
        field: FooBar
    }
    interface FooBar {
        field: NotInTheSchema
    }
    union U = A | B
    input Blob {
        field: UnknownType
    }
    query Foo($var: NotInTheSchema) {
        user(id: $var) {
        id
        }
    }
    ''', [
        'Unknown type "NotInTheSchema"',
    ])
