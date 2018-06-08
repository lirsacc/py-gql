# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

import pytest

from py_gql.validation import FieldsOnCorrectTypeChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_object_field_selection(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment objectFieldSelection on Dog {
        __typename
        name
    }""",
    )


def test_aliased_object_field_selection(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment aliasedObjectFieldSelection on Dog {
        tn : __typename
        otherName : name
    }
    """,
    )


def test_interface_field_selection(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment interfaceFieldSelection on Pet {
        __typename
        name
    }
    """,
    )


def test_aliased_interface_field_selection(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment interfaceFieldSelection on Pet {
        otherName : name
    }
    """,
    )


def test_lying_alias_selection(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment lyingAliasSelection on Dog {
        name : nickname
    }
    """,
    )


def test_ignores_fields_on_unknown_type(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment unknownSelection on UnknownType {
        unknownField
    }
    """,
    )


def test_reports_errors_when_type_is_known_again(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment typeKnownAgain on Pet {
        unknown_pet_field {
            ... on Cat {
                unknown_cat_field
            }
        }
    }
    """,
        [
            'Cannot query field "unknown_pet_field" on type "Pet"',
            'Cannot query field "unknown_cat_field" on type "Cat"',
        ],
    )


def test_field_not_defined_on_fragment(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment fieldNotDefined on Dog {
        meowVolume
    }
    """,
        ['Cannot query field "meowVolume" on type "Dog"'],
    )


def test_ignores_deeply_unknown_field(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment deepFieldNotDefined on Dog {
        unknown_field {
            deeper_unknown_field
        }
    }
    """,
        ['Cannot query field "unknown_field" on type "Dog"'],
    )


def test_sub_field_not_defined(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment subFieldNotDefined on Human {
        pets {
            unknown_field
        }
    }
    """,
        ['Cannot query field "unknown_field" on type "Pet"'],
    )


def test_field_not_defined_on_inline_fragment(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment fieldNotDefined on Pet {
        ... on Dog {
            meowVolume
        }
    }
    """,
        ['Cannot query field "meowVolume" on type "Dog"'],
    )


def test_aliased_field_target_not_defined(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment aliasedFieldTargetNotDefined on Dog {
        volume : mooVolume
    }
    """,
        ['Cannot query field "mooVolume" on type "Dog"'],
    )


def test_aliased_lying_field_target_not_defined(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment aliasedLyingFieldTargetNotDefined on Dog {
        barkVolume : kawVolume
    }
    """,
        ['Cannot query field "kawVolume" on type "Dog"'],
    )


def test_not_defined_on_interface(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment notDefinedOnInterface on Pet {
        tailLength
    }
    """,
        ['Cannot query field "tailLength" on type "Pet"'],
    )


def test_defined_on_implementors_but_not_on_interface(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment definedOnImplementorsButNotInterface on Pet {
        nickname
    }
    """,
        ['Cannot query field "nickname" on type "Pet"'],
    )


def test_meta_field_selection_on_union(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment directFieldSelectionOnUnion on CatOrDog {
        __typename
    }
    """,
    )


def test_direct_field_selection_on_union(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment directFieldSelectionOnUnion on CatOrDog {
        directField
    }
    """,
        ['Cannot query field "directField" on type "CatOrDog"'],
    )


def test_defined_on_implementors_queried_on_union(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment definedOnImplementorsQueriedOnUnion on CatOrDog {
        name
    }
    """,
        ['Cannot query field "name" on type "CatOrDog"'],
    )


def test_valid_field_in_inline_fragment(schema):
    run_test(
        FieldsOnCorrectTypeChecker,
        schema,
        """
    fragment objectFieldSelection on Pet {
        ... on Dog {
            name
        }
        ... {
            name
        }
    }
    """,
    )


# Might be useful to implement when adding the suggestion list
@pytest.mark.skip
def test_works_with_no_suggestions(schema):
    pass


@pytest.mark.skip
def test_works_with_no_small_numbers_of_type_suggestions(schema):
    pass


@pytest.mark.skip
def test_works_with_no_small_numbers_of_field_suggestions(schema):
    pass


@pytest.mark.skip
def test_only_shows_one_set_of_suggestions_at_a_time_preferring_types(schema):
    pass


@pytest.mark.skip
def test_limits_lots_of_type_suggestions(schema):
    pass


@pytest.mark.skip
def test_limits_lots_of_field_suggestions(schema):
    pass
