# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

from py_gql.validation.rules import FieldsOnCorrectTypeChecker

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
            'Cannot query field "unknown_pet_field" on type "Pet".',
            'Cannot query field "unknown_cat_field" on type "Cat".',
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
        [
            'Cannot query field "meowVolume" on type "Dog". '
            'Did you mean "barkVolume"?'
        ],
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
        ['Cannot query field "unknown_field" on type "Dog".'],
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
        ['Cannot query field "unknown_field" on type "Pet".'],
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
        [
            'Cannot query field "meowVolume" on type "Dog". '
            'Did you mean "barkVolume"?'
        ],
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
        [
            'Cannot query field "mooVolume" on type "Dog". '
            'Did you mean "barkVolume"?'
        ],
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
        [
            'Cannot query field "kawVolume" on type "Dog". '
            'Did you mean "barkVolume"?'
        ],
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
        ['Cannot query field "tailLength" on type "Pet".'],
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
        ['Cannot query field "nickname" on type "Pet". Did you mean "name"?'],
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
        [
            'Cannot query field "directField" on type "CatOrDog". '
            'Did you mean to use an inline fragment on "Dog" or "Cat"?'
        ],
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
        [
            'Cannot query field "name" on type "CatOrDog". '
            'Did you mean to use an inline fragment on "Dog" or "Cat"?'
        ],
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
