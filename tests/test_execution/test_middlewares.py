# -*- coding: utf-8 -*-
import asyncio

import pytest

from py_gql._string_utils import stringify_path
from py_gql.execution import AsyncExecutor
from py_gql.execution.middleware import apply_middlewares

from ._test_utils import assert_execution


def test_apply_middlewares_noop_on_empty_args():
    def source(*a, **k):
        return (a, k)

    assert apply_middlewares(source, []) is source


def test_apply_sync_middlewares_on_sync_functions():
    def a(n, *a, **k):
        k["steps"].append("> a")
        return n(*a, **k)

    def b(n, *a, **k):
        k["steps"].append("> b")
        yield n(*a, **k)
        k["steps"].append("< b")

    def c(n, *a, **k):
        k["steps"].append("> c")
        return n(*a, **k)

    def d(n, *a, **k):
        k["steps"].append("> d")
        yield n(*a, **k)
        k["steps"].append("< d")

    def source(*a, **k):
        k["steps"].append("*")
        return (a, k)

    applied = apply_middlewares(source, [a, b, c, d])
    assert applied(42, bar=42, steps=[]) == (
        (42,),
        {"bar": 42, "steps": ["> a", "> b", "> c", "> d", "*", "< d", "< b"]},
    )


@pytest.mark.asyncio
async def test_apply_sync_middleware_on_async_function():
    async def a(n, *a, **k):
        k["steps"].append("> a")
        return await n(*a, **k)

    async def b(n, *a, **k):
        k["steps"].append("> b")
        yield await n(*a, **k)
        k["steps"].append("< b")

    def c(n, *a, **k):
        k["steps"].append("> c")
        return n(*a, **k)

    def d(n, *a, **k):
        k["steps"].append("> d")
        yield n(*a, **k)
        k["steps"].append("< d")

    async def source(*a, **k):
        k["steps"].append("*")
        return (a, k)

    applied = apply_middlewares(source, [a, b, c, d])
    assert await applied(42, bar=42, steps=[]) == (
        (42,),
        {"bar": 42, "steps": ["> a", "> b", "> c", "> d", "*", "< d", "< b"]},
    )


@pytest.mark.asyncio
async def test_apply_sync_middleware_on_sync_function():
    async def a(n, *a, **k):
        print("a", a, k)
        k["steps"].append("> a")
        return await n(*a, **k)

    async def b(n, *a, **k):
        print("b", a, k)
        k["steps"].append("> b")
        yield n(*a, **k)
        k["steps"].append("< b")

    def c(n, *a, **k):
        print("c", a, k)
        k["steps"].append("> c")
        return n(*a, **k)

    def d(n, *a, **k):
        print("d", a, k)
        k["steps"].append("> d")
        yield n(*a, **k)
        k["steps"].append("< d")

    def source(*a, **k):
        k["steps"].append("*")
        return (a, k)

    applied = apply_middlewares(source, [a, b, c, d])
    assert await applied(42, bar=42, steps=[]) == (
        (42,),
        {"bar": 42, "steps": ["> a", "> b", "> c", "> d", "*", "< d", "< b"]},
    )


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

HERO_RESULT = {
    "hero": {
        "friends": [
            {"name": "Luke Skywalker"},
            {"name": "Han Solo"},
            {"name": "Leia Organa"},
        ],
        "id": "2001",
        "name": "R2-D2",
    }
}


@pytest.mark.asyncio
async def test_function_middleware(executor_cls, starwars_schema):
    log = []

    def path_collector_one_way(next_, root, context, info, **args):
        log.append("> %s" % stringify_path(info.path))
        return next_(root, context, info, **args)

    await assert_execution(
        starwars_schema,
        HERO_QUERY,
        middlewares=[path_collector_one_way],
        executor_cls=executor_cls,
        expected_data=HERO_RESULT,
    )

    # Async mode can end up reordeing fields at the same level due to
    # threading wrapper
    assert log[0] == "> hero"
    assert set(log[1:4]) == set(["> hero.id", "> hero.name", "> hero.friends"])
    assert set(log[4:]) == set(
        [
            "> hero.friends[0].name",
            "> hero.friends[1].name",
            "> hero.friends[2].name",
        ]
    )


@pytest.mark.asyncio
async def test_generator_middleware(executor_cls, starwars_schema):
    log = []

    def path_collector(next_, root, context, info, **args):
        log.append("> %s" % stringify_path(info.path))
        yield next_(root, context, info, **args)
        log.append("< %s" % stringify_path(info.path))

    await assert_execution(
        starwars_schema,
        HERO_QUERY,
        middlewares=[path_collector],
        expected_data=HERO_RESULT,
        executor_cls=executor_cls,
    )

    # Async case might re-order fields.
    assert set(log) == set(
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
    )


@pytest.mark.asyncio
async def test_async_generator_middleware(starwars_schema):
    log = []

    class PathCollectorAsync(object):
        async def __call__(self, next_, root, context, info, **args):
            log.append("> %s" % stringify_path(info.path))
            await asyncio.sleep(0.0001)
            yield next_(root, context, info, **args)
            await asyncio.sleep(0.0001)
            log.append("< %s" % stringify_path(info.path))

    path_collector = PathCollectorAsync()

    await assert_execution(
        starwars_schema,
        HERO_QUERY,
        middlewares=[path_collector],
        expected_data=HERO_RESULT,
        executor_cls=AsyncExecutor,
    )

    # Async case might re-order fields.
    assert set(log) == set(
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
    )
