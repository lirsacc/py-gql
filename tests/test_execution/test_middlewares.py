# -*- coding: utf-8 -*-

import collections
import inspect
from typing import List

import pytest

from py_gql import graphql, graphql_blocking
from py_gql._string_utils import stringify_path
from py_gql.exc import ResolverError

from ._test_utils import assert_sync_execution

HERO_QUERY = """
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


def test_sync_path_collector(starwars_schema):
    class PathCollector:
        def __init__(self):
            self.log = []  # type: List[str]

        def __call__(self, next_, root, ctx, info, **args):
            self.log.append("> %s" % stringify_path(info.path))
            res = next_(root, ctx, info, **args)
            self.log.append("< %s" % stringify_path(info.path))
            return res

    path_collector = PathCollector()
    graphql_blocking(starwars_schema, HERO_QUERY, middlewares=[path_collector])

    assert [
        "> hero",
        "< hero",
        "> hero.id",
        "< hero.id",
        "> hero.name",
        "< hero.name",
        "> hero.friends",
        "< hero.friends",
        "> hero.friends[0].name",
        "< hero.friends[0].name",
        "> hero.friends[1].name",
        "< hero.friends[1].name",
        "> hero.friends[2].name",
        "< hero.friends[2].name",
    ] == path_collector.log


@pytest.mark.asyncio
async def test_async_path_collector(starwars_schema):
    class PathCollector:
        def __init__(self):
            self.log = []  # type: List[str]

        async def __call__(self, next_, root, ctx, info, **args):
            self.log.append("> %s" % stringify_path(info.path))
            res = next_(root, ctx, info, **args)
            if inspect.isawaitable(res):
                res = await res
            self.log.append("< %s" % stringify_path(info.path))
            return res

    path_collector = PathCollector()
    await graphql(starwars_schema, HERO_QUERY, middlewares=[path_collector])

    # Async can lead to non-deterministic ordering
    assert set(
        [
            "> hero",
            "< hero",
            "> hero.id",
            "< hero.id",
            "> hero.name",
            "< hero.name",
            "> hero.friends",
            "< hero.friends",
            "> hero.friends[0].name",
            "< hero.friends[0].name",
            "> hero.friends[1].name",
            "< hero.friends[1].name",
            "> hero.friends[2].name",
            "< hero.friends[2].name",
        ]
    ) == set(path_collector.log)


def test_bail_out_in_middleware(starwars_schema):
    def block_deep_fields(next_, root, ctx, info, **args):
        if len(info.path) > 3:
            raise ResolverError("Query too deep.")
        return next_(root, ctx, info, **args)

    assert_sync_execution(
        starwars_schema,
        """
        {
            luke: human(id: "1000") {
                id
                name
                friends {
                    id
                    name
                }
            }

            han: human(id: "1002") {
                id
                name
                friends {
                    id
                    name
                }
            }
        }
        """,
        middlewares=[block_deep_fields],
        expected_data={
            "han": {
                "friends": [
                    {"id": None, "name": None},
                    {"id": None, "name": None},
                    {"id": None, "name": None},
                ],
                "id": "1002",
                "name": "Han Solo",
            },
            "luke": {
                "friends": [
                    {"id": None, "name": None},
                    {"id": None, "name": None},
                    {"id": None, "name": None},
                    {"id": None, "name": None},
                ],
                "id": "1000",
                "name": "Luke Skywalker",
            },
        },
        expected_errors=[
            ("Query too deep.", (86, 88), "luke.friends[0].id"),
            ("Query too deep.", (101, 105), "luke.friends[0].name"),
            ("Query too deep.", (86, 88), "luke.friends[1].id"),
            ("Query too deep.", (101, 105), "luke.friends[1].name"),
            ("Query too deep.", (86, 88), "luke.friends[2].id"),
            ("Query too deep.", (101, 105), "luke.friends[2].name"),
            ("Query too deep.", (86, 88), "luke.friends[3].id"),
            ("Query too deep.", (101, 105), "luke.friends[3].name"),
            ("Query too deep.", (206, 208), "han.friends[0].id"),
            ("Query too deep.", (221, 225), "han.friends[0].name"),
            ("Query too deep.", (206, 208), "han.friends[1].id"),
            ("Query too deep.", (221, 225), "han.friends[1].name"),
            ("Query too deep.", (206, 208), "han.friends[2].id"),
            ("Query too deep.", (221, 225), "han.friends[2].name"),
        ],
    )


def test_middlewares_chain(starwars_schema):

    context = collections.defaultdict(int)  # type: ignore

    def add_to_chain(next_, root, ctx, info, **args):
        ctx[tuple(info.path)] += 1
        return next_(root, ctx, info, **args)

    graphql_blocking(
        starwars_schema,
        "{ hero { id } }",
        context=context,
        middlewares=[add_to_chain, add_to_chain, add_to_chain],
    )

    assert {("hero",): 3, ("hero", "id"): 3} == context
