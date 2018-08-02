# -*- coding: utf-8 -*-
""" Test the main async/await entry point """

import asyncio
from concurrent.futures import CancelledError

import pytest

from py_gql.asyncio import graphql, AsyncIOExecutor
from py_gql.exc import SchemaError
from py_gql.schema import String, Schema, ObjectType, Field
from py_gql.execution import _concurrency


@pytest.mark.asyncio
async def test_it_correctly_identifies_r2_d2_as_the_hero_of_the_star_wars_saga(
    starwars_schema
):
    result = await graphql(
        starwars_schema,
        """
        query HeroNameQuery {
            hero {
            name
            }
        }
        """,
    )
    assert result.response() == {"data": {"hero": {"name": "R2-D2"}}}


@pytest.mark.asyncio
async def test_correct_response_on_syntax_error_1(starwars_schema):
    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, "", {}, executor=executor)

    assert result.response() == {
        "errors": [
            {
                "message": "Unexpected <EOF> (1:1):\n  1:\n    ^",
                "locations": [{"columne": 1, "line": 1}],
            }
        ]
    }


@pytest.mark.asyncio
async def test_correct_response_on_syntax_error_2(starwars_schema):
    query = """
    query HeroNameQuery {{
        hero {
           name
        }
    }
    """

    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, query, {}, executor=executor)

    assert result.response() == {
        "errors": [
            {
                "message": """Expected Name but found "{" (2:26):
  1:
  2:    query HeroNameQuery {{
                             ^
  3:        hero {
  4:           name""",
                "locations": [{"columne": 26, "line": 2}],
            }
        ]
    }


@pytest.mark.asyncio
async def test_correct_response_on_validation_errors(starwars_schema):
    query = """
    query HeroNameAndFriendsQuery($hero: Droid) {
        hero {
            id
            foo
            friends {
                name
            }
        }
    }

    fragment hero on Character {
        id
        friends { name }
    }
    """

    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, query, {}, executor=executor)

    assert result.response() == {
        "errors": [
            {
                "locations": [{"column": 35, "line": 2}],
                "message": 'Variable "$hero" must be input type',
            },
            {
                "locations": [{"column": 13, "line": 5}],
                "message": 'Cannot query field "foo" on type "Character"',
            },
            {"message": 'Unused fragment(s) "hero"'},
            {
                "locations": [{"column": 35, "line": 2}],
                "message": 'Unused variable "$hero"',
            },
        ]
    }


@pytest.mark.asyncio
async def test_correct_response_on_argument_validation_error(starwars_schema):
    query = """
    query HeroNameQuery {
        luke: human {
            name
        }
    }
    """
    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, query, {}, executor=executor)

    assert result.response() == {
        "errors": [
            {
                "message": (
                    'Field "human" argument "id" of type String! '
                    "is required but not provided"
                ),
                "locations": [{"line": 3, "column": 9}],
            }
        ]
    }


@pytest.mark.asyncio
async def test_correct_response_on_execution_error(starwars_schema):
    query = """
    query HeroNameAndFriendsQuery {
        hero {
            id
            friends {
                name
            }
        }
    }

    query HeroNameQuery {
        hero {
           name
        }
    }
    """

    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, query, {}, executor=executor)

    assert result.response() == {
        "errors": [
            {
                "message": "Operation name is required when document contains "
                "multiple operation definitions"
            }
        ],
        "data": None,
    }


@pytest.mark.asyncio
async def test_correct_response_on_execution_error_2(starwars_schema):
    query = """
    query HeroNameAndFriendsQuery {
        hero {
            id
            friends {
                name
            }
        }
    }

    query HeroNameQuery {
        hero {
           name
        }
    }
    """

    with AsyncIOExecutor() as executor:
        result = await graphql(
            starwars_schema, query, {}, operation_name="Foo", executor=executor
        )

    assert result.response() == {
        "errors": [{"message": 'No operation "Foo" found in document'}],
        "data": None,
    }


@pytest.mark.asyncio
async def test_correct_response_on_execution_error_3(starwars_schema):
    query = """
    mutation  {
        hero {
            id
            friends {
                name
            }
        }
    }
    """
    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, query, {}, executor=executor)

    assert result.response() == {
        "errors": [{"message": "Schema doesn't support mutation operation"}],
        "data": None,
    }


@pytest.mark.asyncio
async def test_correct_response_on_variables_error(starwars_schema):
    query = """
    query ($episode: Episode!, $human: String!) {
        hero(episode: $episode) {
            name
        }
        human(id: $human) {
            name
        }
    }
    """

    with AsyncIOExecutor() as executor:
        result = await graphql(
            starwars_schema, query, {"episode": 42, "id": 42}, executor=executor
        )

    assert result.response() == {
        "errors": [
            {
                "message": (
                    'Variable "$episode" got invalid value 42 '
                    "(Expected type Episode)"
                ),
                "locations": [{"line": 2, "column": 12}],
            },
            {
                "message": (
                    'Variable "$human" of required type "String!" '
                    "was not provided."
                ),
                "locations": [{"line": 2, "column": 32}],
            },
        ],
        "data": None,
    }


@pytest.mark.asyncio
async def test_correct_response_on_resolver_error(starwars_schema):
    query = """
    query HeroNameQuery {
        mainHero: hero {
            name
            story: secretBackstory
        }
    }
    """
    with AsyncIOExecutor() as executor:
        result = await graphql(starwars_schema, query, {}, executor=executor)

    assert result.response() == {
        "errors": [
            {
                "message": "secretBackstory is secret.",
                "locations": [{"line": 5, "column": 13}],
                "path": ["mainHero", "story"],
                "extensions": {"code": 42},
            }
        ],
        "data": {"mainHero": {"name": "R2-D2", "story": None}},
    }


@pytest.mark.asyncio
async def test_raises_if_invalid_schema_is_provided():
    with pytest.raises(SchemaError) as exc_info:
        await graphql(Schema(String), "{ field }", {})
    assert str(exc_info.value) == 'Query must be ObjectType but got "String"'


@pytest.mark.asyncio
async def test_async_resolvers():
    async def resolve_x(root, args, ctx, info):
        await asyncio.sleep(0.25)
        return root.get("x", None)

    obj = ObjectType("Object", [Field("x", String, resolve=resolve_x)])
    schema = Schema(obj)

    result = await graphql(schema, "{ x }", initial_value={"x": "foo"})

    assert result.response() == {"data": {"x": "foo"}}


async def _async_func(x):
    await asyncio.sleep(.1)
    return x


async def _non_async_func(x):
    return x


class TestAsyncIOExecutor(object):
    @pytest.mark.asyncio
    async def test_submit_returns_a_future(self):
        f = AsyncIOExecutor().submit(_async_func, 1)
        assert _concurrency.is_deferred(f)
        r = await f
        assert r == 1

    @pytest.mark.asyncio
    async def test_submit_accepts_non_async_functions(self):
        f = AsyncIOExecutor().submit(_non_async_func, 1)
        assert _concurrency.is_deferred(f)
        r = await f
        assert r == 1

    @pytest.mark.asyncio
    async def test_shutdowns_cancels_remaining_tasks(self):
        with AsyncIOExecutor() as e:
            f = e.submit(_async_func, 1)

        with pytest.raises(CancelledError):
            await f

    @pytest.mark.asyncio
    async def test_shutdowns_leaves_done_tasks_alone(self):
        with AsyncIOExecutor() as e:
            f = e.submit(_async_func, 1)
            assert await f == 1
        assert await f == 1

    @pytest.mark.asyncio
    async def test_rejects_futures_after_shutdown(self):
        with AsyncIOExecutor() as e:
            f = e.submit(_async_func, 1)
            await f

        with pytest.raises(RuntimeError):
            e.submit(_async_func, 1)
