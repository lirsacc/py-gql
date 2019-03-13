# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

from py_gql.validation.rules import PossibleFragmentSpreadsChecker

from .._test_utils import assert_checker_validation_result as run_test


def test_of_the_same_object(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment objectWithinObject on Dog { ...dogFragment }
        fragment dogFragment on Dog { barkVolume }
        """,
    )


def test_of_the_same_object_with_inline_fragment(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment objectWithinObjectAnon on Dog { ... on Dog { barkVolume } }
        """,
    )


def test_object_into_an_implemented_interface(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment objectWithinInterface on Pet { ...dogFragment }
        fragment dogFragment on Dog { barkVolume }
        """,
    )


def test_object_into_containing_union(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment objectWithinUnion on CatOrDog { ...dogFragment }
        fragment dogFragment on Dog { barkVolume }
        """,
    )


def test_union_into_contained_object(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment unionWithinObject on Dog { ...catOrDogFragment }
        fragment catOrDogFragment on CatOrDog { __typename }
        """,
    )


def test_union_into_overlapping_interface(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment unionWithinInterface on Pet { ...catOrDogFragment }
        fragment catOrDogFragment on CatOrDog { __typename }
        """,
    )


def test_union_into_overlapping_union(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment unionWithinUnion on DogOrHuman { ...catOrDogFragment }
        fragment catOrDogFragment on CatOrDog { __typename }
        """,
    )


def test_interface_into_implemented_object(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment interfaceWithinObject on Dog { ...petFragment }
        fragment petFragment on Pet { name }
        """,
    )


def test_interface_into_overlapping_interface(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment interfaceWithinInterface on Pet { ...beingFragment }
        fragment beingFragment on Being { name }
        """,
    )


def test_interface_into_overlapping_interface_in_inline_fragment(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment interfaceWithinInterface on Pet { ... on Being { name } }
        """,
    )


def test_interface_into_overlapping_union(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment interfaceWithinUnion on CatOrDog { ...petFragment }
        fragment petFragment on Pet { name }
        """,
    )


def test_ignores_incorrect_type_caught_by_FragmentsOnCompositeTypes(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment petFragment on Pet { ...badInADifferentWay }
        fragment badInADifferentWay on String { name }
        """,
    )


def test_different_object_into_object(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidObjectWithinObject on Cat { ...dogFragment }
        fragment dogFragment on Dog { barkVolume }
        """,
        [
            'Fragment "dogFragment" cannot be spread here as types "Dog" and '
            '"Cat" do not overlap.'
        ],
    )


def test_different_object_into_object_in_inline_fragment(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidObjectWithinObjectAnon on Cat {
            ... on Dog { barkVolume }
        }
        """,
        [
            'Inline fragment cannot be spread here as types "Dog" and "Cat" '
            "do not overlap."
        ],
    )


def test_object_into_not_implementing_interface(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidObjectWithinInterface on Pet { ...humanFragment }
        fragment humanFragment on Human { pets { name } }
        """,
        [
            'Fragment "humanFragment" cannot be spread here as types "Human" '
            'and "Pet" do not overlap.'
        ],
    )


def test_object_into_not_containing_union(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidObjectWithinUnion on CatOrDog { ...humanFragment }
        fragment humanFragment on Human { pets { name } }
        """,
        [
            'Fragment "humanFragment" cannot be spread here as types "Human" '
            'and "CatOrDog" do not overlap.'
        ],
    )


def test_union_into_not_contained_object(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidUnionWithinObject on Human { ...catOrDogFragment }
        fragment catOrDogFragment on CatOrDog { __typename }
        """,
        [
            'Fragment "catOrDogFragment" cannot be spread here as types '
            '"CatOrDog" and "Human" do not overlap.'
        ],
    )


def test_union_into_non_overlapping_interface(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidUnionWithinInterface on Pet { ...humanOrAlienFragment }
        fragment humanOrAlienFragment on HumanOrAlien { __typename }
        """,
        [
            'Fragment "humanOrAlienFragment" cannot be spread here as types '
            '"HumanOrAlien" and "Pet" do not overlap.'
        ],
    )


def test_union_into_non_overlapping_union(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidUnionWithinUnion on CatOrDog { ...humanOrAlienFragment }
        fragment humanOrAlienFragment on HumanOrAlien { __typename }
        """,
        [
            'Fragment "humanOrAlienFragment" cannot be spread here as types '
            '"HumanOrAlien" and "CatOrDog" do not overlap.'
        ],
    )


def test_interface_into_non_implementing_object(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidInterfaceWithinObject on Cat { ...intelligentFragment }
        fragment intelligentFragment on Intelligent { iq }
        """,
        [
            'Fragment "intelligentFragment" cannot be spread here as types '
            '"Intelligent" and "Cat" do not overlap.'
        ],
    )


def test_interface_into_non_overlapping_interface(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidInterfaceWithinInterface on Pet {
            ...intelligentFragment
        }
        fragment intelligentFragment on Intelligent { iq }
        """,
        [
            'Fragment "intelligentFragment" cannot be spread here as types '
            '"Intelligent" and "Pet" do not overlap.'
        ],
    )


def test_interface_into_non_overlapping_interface_in_inline_fragment(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidInterfaceWithinInterfaceAnon on Pet {
            ...on Intelligent { iq }
        }
        """,
        [
            'Inline fragment cannot be spread here as types "Intelligent" '
            'and "Pet" do not overlap.'
        ],
    )


def test_interface_into_non_overlapping_union(schema):
    run_test(
        PossibleFragmentSpreadsChecker,
        schema,
        """
        fragment invalidInterfaceWithinUnion on HumanOrAlien { ...petFragment }
        fragment petFragment on Pet { name }
        """,
        [
            'Fragment "petFragment" cannot be spread here as types "Pet" and '
            '"HumanOrAlien" do not overlap.'
        ],
    )
