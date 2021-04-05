# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are applicable but
# they conserved as comments for reference.


from py_gql.validation.rules import FragmentsOnCompositeTypesChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_object_is_valid_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment validFragment on Dog {
            barks
        }
        """,
    )


def test_interface_is_valid_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment validFragment on Pet {
            name
        }
        """,
    )


def test_object_is_valid_inline_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment validFragment on Pet {
            ... on Dog {
                barks
            }
        }
        """,
    )


def test_inline_fragment_without_type_is_valid(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment validFragment on Pet {
            ... {
                name
            }
        }
        """,
    )


def test_union_is_valid_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment validFragment on CatOrDog {
            __typename
        }
        """,
    )


def test_scalar_is_invalid_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment scalarFragment on Boolean {
            bad
        }
        """,
        [
            'Fragment "scalarFragment" cannot condition on non composite type '
            '"Boolean".',
        ],
    )


def test_enum_is_invalid_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment scalarFragment on FurColor {
            bad
        }
        """,
        [
            'Fragment "scalarFragment" cannot condition on non composite type '
            '"FurColor".',
        ],
    )


def test_input_object_is_invalid_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment inputFragment on ComplexInput {
            stringField
        }
        """,
        [
            'Fragment "inputFragment" cannot condition on non composite type '
            '"ComplexInput".',
        ],
    )


def test_scalar_is_invalid_inline_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment invalidFragment on Pet {
            ... on String {
                barks
            }
        }
        """,
        ['Fragment cannot condition on non composite type "String".'],
    )


def test_interface_is_valid_inling_fragment_type(schema):
    run_test(
        FragmentsOnCompositeTypesChecker,
        schema,
        """
        fragment validFragment on Mammal {
            ... on Canine {
               name
            }
        }
        """,
    )
