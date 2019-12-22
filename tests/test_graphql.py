# -*- coding: utf-8 -*-
""" Test the main entry point """

import asyncio

import pytest

from py_gql._graphql import graphql, graphql_blocking, process_graphql_query
from py_gql.exc import ResolverError, SchemaError
from py_gql.execution.runtime import ThreadPoolRuntime
from py_gql.schema import Schema, String
from py_gql.sdl import build_schema


async def _execute_query_blocking(*args, **kwargs):
    return graphql_blocking(*args, **kwargs)


async def _execute_query_async(*args, **kwargs):
    return await graphql(*args, **kwargs)


async def _execute_query_threaded(*args, **kwargs):
    return process_graphql_query(
        *args, runtime=ThreadPoolRuntime(), **kwargs
    ).result()


_with_execution_strategies = pytest.mark.parametrize(
    "execute_query",
    [_execute_query_blocking, _execute_query_async, _execute_query_threaded],
)


@pytest.mark.asyncio
@_with_execution_strategies
async def test_it_correctly_identifies_r2_d2_as_the_hero_sync(
    starwars_schema, execute_query
):
    result = await execute_query(
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
@_with_execution_strategies
async def test_correct_response_on_syntax_error_1(
    execute_query, starwars_schema
):
    assert (await execute_query(starwars_schema, "")).response() == {
        "errors": [
            {
                "message": "Unexpected <EOF> (1:1):\n  1:\n    ^\n",
                "locations": [{"columne": 1, "line": 1}],
            }
        ]
    }


@pytest.mark.asyncio
@_with_execution_strategies
async def test_correct_response_on_syntax_error_2(
    execute_query, starwars_schema
):
    query = """
    query HeroNameQuery {{
        hero {
           name
        }
    }
    """

    assert (await execute_query(starwars_schema, query)).response() == {
        "errors": [
            {
                "message": """Expected Name but found "{" (2:26):
  1:
  2:    query HeroNameQuery {{
                             ^
  3:        hero {
  4:           name
""",
                "locations": [{"columne": 26, "line": 2}],
            }
        ]
    }


@pytest.mark.asyncio
@_with_execution_strategies
async def test_correct_response_on_validation_errors(
    execute_query, starwars_schema
):
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
    assert (await execute_query(starwars_schema, query)).response() == {
        "errors": [
            {
                "locations": [{"column": 35, "line": 2}],
                "message": 'Variable "$hero" must be input type',
            },
            {
                "locations": [{"column": 13, "line": 5}],
                "message": 'Cannot query field "foo" on type "Character".',
            },
            {"message": 'Unused fragment(s) "hero"'},
            {
                "locations": [{"column": 35, "line": 2}],
                "message": 'Unused variable "$hero"',
            },
        ]
    }


@pytest.mark.asyncio
@_with_execution_strategies
async def test_correct_response_on_argument_validation_error(
    execute_query, starwars_schema
):
    query = """
    query HeroNameQuery {
        luke: human {
            name
        }
    }
    """
    assert (await execute_query(starwars_schema, query)).response() == {
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
@_with_execution_strategies
async def test_correct_response_on_execution_error(
    execute_query, starwars_schema
):
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
    assert (await execute_query(starwars_schema, query)).response() == {
        "errors": [
            {
                "message": "Operation name is required when document contains "
                "multiple operation definitions"
            }
        ],
        "data": None,
    }


@pytest.mark.asyncio
@_with_execution_strategies
async def test_correct_response_on_execution_error_2(
    execute_query, starwars_schema
):
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
    assert (
        await execute_query(starwars_schema, query, operation_name="Foo")
    ).response() == {
        "errors": [{"message": 'No operation "Foo" in document'}],
        "data": None,
    }


@pytest.mark.asyncio
@_with_execution_strategies
async def test_correct_response_on_execution_error_3(
    execute_query, starwars_schema
):
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
    assert (await execute_query(starwars_schema, query)).response() == {
        "errors": [{"message": "Schema doesn't support mutation operation"}],
        "data": None,
    }


@pytest.mark.asyncio
@_with_execution_strategies
async def test_correct_response_on_variables_error(
    execute_query, starwars_schema
):
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
    assert (
        await execute_query(
            starwars_schema, query, variables={"episode": 42, "id": 42}
        )
    ).response() == {
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
@_with_execution_strategies
async def test_correct_response_on_resolver_error(
    execute_query, starwars_schema
):
    query = """
    query HeroNameQuery {
        mainHero: hero {
            name
            story: secretBackstory
        }
    }
    """
    assert (await execute_query(starwars_schema, query)).response() == {
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
@_with_execution_strategies
async def test_raises_if_invalid_schema_is_provided(execute_query):
    schema = Schema(String)  # type: ignore
    with pytest.raises(SchemaError) as exc_info:
        await execute_query(schema, "{ field }")
    assert str(exc_info.value) == 'Query must be ObjectType but got "String"'


@pytest.mark.asyncio
async def test_graphql_with_async_resolvers():
    schema = build_schema(
        """
        type Query {
            foo: String
            bar(value: Int!): Int
            baz: String
        }
        """
    )

    @schema.resolver("Query.foo")
    async def resolve_foo(*_):
        await asyncio.sleep(0.001)
        return "Foo"

    @schema.resolver("Query.bar")
    async def resolve_bar(*_, value):
        await asyncio.sleep(0.001)
        return value

    @schema.resolver("Query.baz")
    async def resolve_baz(*_):
        raise ResolverError("Baz Error")

    result = await graphql(schema, "{ foo, bar(value: 42), baz }")
    assert {
        "data": {"bar": 42, "foo": "Foo", "baz": None},
        "errors": [
            {
                "locations": [{"column": 24, "line": 1}],
                "message": "Baz Error",
                "path": ["baz"],
            }
        ],
    } == result.response()
