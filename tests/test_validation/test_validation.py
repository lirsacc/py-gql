# -*- coding: utf-8 -*-
""" Test default validation. """

from ._test_utils import assert_validation_result


def test_it_validates_queries(schema):
    assert_validation_result(
        schema,
        """
        query {
            catOrDog {
                ... on Cat {
                    furColor
                }
                ... on Dog {
                isHousetrained
                }
            }
        }
        """,
    )


def test_it_detects_bad_scalar_parse(schema):
    assert_validation_result(
        schema,
        """
        query {
            invalidArg(arg: "bad value")
        }
        """,
        [
            'Expected type Invalid, found "bad value" '
            "(Invalid scalar is always invalid)"
        ],
    )


# Star Wars schema related tests


def test_complex_but_valid_query(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query NestedQueryWithFragment {
            hero {
                ...NameAndAppearances
                friends {
                    ...NameAndAppearances
                    friends {
                    ...NameAndAppearances
                    }
                }
            }
        }

        fragment NameAndAppearances on Character {
            name
            appearsIn
        }
        """,
    )


def test_non_existent_fields_are_invalid(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query HeroSpaceshipQuery {
            hero {
            favoriteSpaceship
            }
        }
        """,
        ['Cannot query field "favoriteSpaceship" on type "Character".'],
    )


def test_requires_fields_on_objects(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query HeroNoFieldsQuery {
            hero
        }
        """,
        [
            'Field "hero" of type "Character" must have a selection of subfields. '
            'Did you mean "hero { ... }"?'
        ],
    )


def test_disallows_fields_on_scalars(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query HeroFieldsOnScalarQuery {
            hero {
                name {
                    firstCharacterOfName
                }
            }
        }
        """,
        [
            'Field "name" must not have a selection since type "String" '
            "has no subfields."
        ],
    )


def test_disallows_object_fields_on_interface(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query DroidFieldOnCharacter {
            hero {
                name
                primaryFunction
            }
        }
        """,
        ['Cannot query field "primaryFunction" on type "Character".'],
    )


def test_allows_object_fields_in_fragments(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query DroidFieldInFragment {
            hero {
                name
            ...DroidFields
            }
        }

        fragment DroidFields on Droid {
            primaryFunction
        }
        """,
    )


def test_allows_object_fields_in_inline_fragments(starwars_schema):
    assert_validation_result(
        starwars_schema,
        """
        query DroidFieldInFragment {
            hero {
                name
                ... on Droid {
                    primaryFunction
                }
            }
        }
        """,
    )
