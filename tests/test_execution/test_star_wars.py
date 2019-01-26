# -*- coding: utf-8 -*-

import pytest

from py_gql.lang import parse

from ._test_utils import assert_execution

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_it_correctly_identifies_r2_d2_as_the_hero_of_the_star_wars_saga(
    starwars_schema, executor_cls
):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query HeroNameQuery {
                hero {
                    name
                    id
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={"hero": {"name": "R2-D2", "id": "2001"}},
    )


async def test_id_and_friends_of_r2_d2(starwars_schema, executor_cls):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query HeroNameAndFriendsQuery {
                hero {
                    id
                    name
                    friends {
                        name
                    }
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={
            "hero": {
                "id": "2001",
                "name": "R2-D2",
                "friends": [
                    {"name": "Luke Skywalker"},
                    {"name": "Han Solo"},
                    {"name": "Leia Organa"},
                ],
            }
        },
    )


async def test_the_friends_of_friends_of_r2_d2(starwars_schema, executor_cls):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query NestedQuery {
                hero {
                    name
                    friends {
                        name
                        appearsIn
                        friends {
                        name
                        }
                    }
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={
            "hero": {
                "name": "R2-D2",
                "friends": [
                    {
                        "name": "Luke Skywalker",
                        "appearsIn": ["NEWHOPE", "EMPIRE", "JEDI"],
                        "friends": [
                            {"name": "Han Solo"},
                            {"name": "Leia Organa"},
                            {"name": "C-3PO"},
                            {"name": "R2-D2"},
                        ],
                    },
                    {
                        "name": "Han Solo",
                        "appearsIn": ["NEWHOPE", "EMPIRE", "JEDI"],
                        "friends": [
                            {"name": "Luke Skywalker"},
                            {"name": "Leia Organa"},
                            {"name": "R2-D2"},
                        ],
                    },
                    {
                        "name": "Leia Organa",
                        "appearsIn": ["NEWHOPE", "EMPIRE", "JEDI"],
                        "friends": [
                            {"name": "Luke Skywalker"},
                            {"name": "Han Solo"},
                            {"name": "C-3PO"},
                            {"name": "R2-D2"},
                        ],
                    },
                ],
            }
        },
    )


async def test_luke_skywalker_using_id(starwars_schema, executor_cls):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query FetchLukeQuery {
                human(id: "1000") {
                name
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={"human": {"name": "Luke Skywalker"}},
    )


@pytest.mark.parametrize(
    "id_, expected",
    [
        ("1000", {"name": "Luke Skywalker"}),
        ("1002", {"name": "Han Solo"}),
        ("not a valid id", None),
    ],
)
async def test_generic_query_using_id_and_variable(
    starwars_schema, executor_cls, id_, expected
):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query FetchSomeIDQuery($someId: String!) {
                human(id: $someId) {
                name
                }
            }
            """
        ),
        variables={"someId": id_},
        executor_cls=executor_cls,
        expected_data={"human": expected},
    )


async def test_changing_key_with_alias(starwars_schema, executor_cls):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query FetchLukeAliased {
                luke: human(id: "1000") {
                name
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={"luke": {"name": "Luke Skywalker"}},
    )


async def test_same_root_field_multiple_aliases(starwars_schema, executor_cls):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query FetchLukeAndLeiaAliased {
                luke: human(id: "1000") {
                    name
                    homePlanet
                }
                leia: human(id: "1003") {
                    name
                    homePlanet
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={
            "luke": {"name": "Luke Skywalker", "homePlanet": "Tatooine"},
            "leia": {"name": "Leia Organa", "homePlanet": "Alderaan"},
        },
    )


async def test_use_of_fragment_to_avoid_duplicate_content(
    starwars_schema, executor_cls
):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query FetchLukeAndLeiaAliased {
                luke: human(id: "1000") { ...HumanFragment }
                leia: human(id: "1003") { ...HumanFragment }
            }

            fragment HumanFragment on Human { name homePlanet }
            """
        ),
        executor_cls=executor_cls,
        expected_data={
            "luke": {"name": "Luke Skywalker", "homePlanet": "Tatooine"},
            "leia": {"name": "Leia Organa", "homePlanet": "Alderaan"},
        },
    )


@pytest.mark.parametrize(
    "query, result",
    [
        (
            "query CheckTypeOfR2 { hero { __typename name } }",
            {"hero": {"__typename": "Droid", "name": "R2-D2"}},
        ),
        (
            "query CheckTypeOfLuke { hero(episode: EMPIRE) { __typename name } }",
            {"hero": {"__typename": "Human", "name": "Luke Skywalker"}},
        ),
    ],
)
async def test_introspection(starwars_schema, executor_cls, query, result):
    await assert_execution(
        starwars_schema,
        parse(query),
        expected_data=result,
        executor_cls=executor_cls,
    )


async def test_error_on_accessing_secret_backstory(
    starwars_schema, executor_cls
):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query HeroNameQuery {
                hero {
                    name
                    secretBackstory
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={"hero": {"name": "R2-D2", "secretBackstory": None}},
        expected_errors=[
            ("secretBackstory is secret.", (103, 118), "hero.secretBackstory")
        ],
    )


async def test_error_on_accessing_secret_backstory_in_a_list(
    starwars_schema, executor_cls
):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query HeroNameQuery {
                hero {
                    name
                    friends {
                        name
                        secretBackstory
                    }
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={
            "hero": {
                "friends": [
                    {"name": "Luke Skywalker", "secretBackstory": None},
                    {"name": "Han Solo", "secretBackstory": None},
                    {"name": "Leia Organa", "secretBackstory": None},
                ],
                "name": "R2-D2",
            }
        },
        expected_errors=[
            (
                "secretBackstory is secret.",
                (166, 181),
                "hero.friends[%d].secretBackstory" % i,
            )
            for i in range(3)
        ],
    )


async def test_error_on_accessing_secret_backstory_through_alias(
    starwars_schema, executor_cls
):
    await assert_execution(
        starwars_schema,
        parse(
            """
            query HeroNameQuery {
                mainHero: hero {
                    name
                    story: secretBackstory
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={"mainHero": {"name": "R2-D2", "story": None}},
        expected_errors=[
            ("secretBackstory is secret.", (113, 135), "mainHero.story")
        ],
    )


async def test_error_on_missing_argument(starwars_schema, executor_cls):
    await assert_execution(
        starwars_schema,
        parse(
            """
            {
                luke: human {
                    name
                }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={"luke": None},
        expected_errors=[
            (
                'Argument "id" of required type "String!" was not provided',
                (31, 87),
                "luke",
            )
        ],
    )
