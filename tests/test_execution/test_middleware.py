# -*- coding: utf-8 -*-

import pytest

from py_gql._graphql import graphql
from py_gql._string_utils import stringify_path
from py_gql.execution.middleware import GraphQLMiddleware, apply_middlewares
from py_gql.execution import ThreadPoolExecutor

from ._test_utils import TESTED_EXECUTORS


def test_apply_middlewares():
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

    def source(*a, **k):
        return (a, k)

    assert apply_middlewares(source, [a, b, c])(42, bar=42, steps=[]) == (
        (42,),
        {"bar": 42, "steps": ["> a", "> b", "> c", "< b"]},
    )


def test_apply_middlewares_noop():
    def source(*a, **k):
        return (a, k)

    assert apply_middlewares(source, []) is source


def test_apply_middlewares_no_yield():
    def never_yields(n, *a, **k):
        # pylint: disable = using-constant-test
        if False:
            yield n(*a, **k)

    def source(*a, **k):
        return (a, k)

    with pytest.raises(RuntimeError):
        apply_middlewares(source, [never_yields])(42)


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


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_function_middleware(exe_cls, exe_kwargs, starwars_schema):
    log = []

    def path_collector_one_way(next_, root, args, context, info):
        log.append("> %s" % stringify_path(info.path))
        return next_(root, args, context, info)

    with exe_cls(**exe_kwargs) as executor:
        graphql(
            starwars_schema,
            HERO_QUERY,
            middlewares=[path_collector_one_way],
            executor=executor,
        )

    assert log == [
        "> hero",
        "> hero.id",
        "> hero.name",
        "> hero.friends",
        "> hero.friends[0].name",
        "> hero.friends[1].name",
        "> hero.friends[2].name",
    ]


def test_generator_middleware(starwars_schema):
    log = []

    def path_collector(next_, root, args, context, info):
        log.append("> %s" % stringify_path(info.path))
        yield next_(root, args, context, info)
        log.append("< %s" % stringify_path(info.path))

    graphql(starwars_schema, HERO_QUERY, middlewares=[path_collector])

    assert log == [
        "> hero",
        "> hero.id",
        "< hero.id",
        "> hero.name",
        "< hero.name",
        "> hero.friends",
        "> hero.friends[0].name",
        "< hero.friends[0].name",
        "> hero.friends[1].name",
        "< hero.friends[1].name",
        "> hero.friends[2].name",
        "< hero.friends[2].name",
        "< hero.friends",
        "< hero",
    ]


def test_generator_middleware_with_threads(starwars_schema):
    log = set()

    def path_collector(next_, root, args, context, info):
        log.add("> %s" % stringify_path(info.path))
        yield next_(root, args, context, info)
        log.add("< %s" % stringify_path(info.path))

    with ThreadPoolExecutor(max_workers=10) as executor:
        graphql(
            starwars_schema,
            HERO_QUERY,
            middlewares=[path_collector],
            executor=executor,
        )

    assert log == set(
        [
            "> hero",
            "> hero.id",
            "< hero.id",
            "> hero.name",
            "< hero.name",
            "> hero.friends",
            "> hero.friends[0].name",
            "< hero.friends[0].name",
            "> hero.friends[1].name",
            "< hero.friends[1].name",
            "> hero.friends[2].name",
            "< hero.friends[2].name",
            "< hero.friends",
            "< hero",
        ]
    )


class PathCollectorMiddleware(GraphQLMiddleware):
    def __init__(self):
        self.log = []

    def __call__(self, next_, root, args, context, info):
        self.log.append("> %s" % stringify_path(info.path))
        yield next_(root, args, context, info)
        self.log.append("< %s" % stringify_path(info.path))


def test_class_based_middleware(starwars_schema):
    path_collector = PathCollectorMiddleware()
    graphql(starwars_schema, HERO_QUERY, middlewares=[path_collector])

    assert path_collector.log == [
        "> hero",
        "> hero.id",
        "< hero.id",
        "> hero.name",
        "< hero.name",
        "> hero.friends",
        "> hero.friends[0].name",
        "< hero.friends[0].name",
        "> hero.friends[1].name",
        "< hero.friends[1].name",
        "> hero.friends[2].name",
        "< hero.friends[2].name",
        "< hero.friends",
        "< hero",
    ]
