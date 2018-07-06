# -*- coding: utf-8 -*-

import pytest

from py_gql._graphql import graphql
from py_gql.execution.middleware import GraphQLMiddleware, apply_middlewares


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


def test_function_middleware(starwars_schema):
    log = []

    def path_collector_one_way(next_, root, args, context, info):
        log.append("> %s" % info.path)
        return next_(root, args, context, info)

    graphql(starwars_schema, HERO_QUERY, middlewares=[path_collector_one_way])

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

    def path_collector_one_way(next_, root, args, context, info):
        log.append("> %s" % info.path)
        yield next_(root, args, context, info)
        log.append("< %s" % info.path)

    graphql(starwars_schema, HERO_QUERY, middlewares=[path_collector_one_way])

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


class PathCollectorMiddleware(GraphQLMiddleware):
    def __init__(self):
        self.log = []

    def __call__(self, next_, root, args, context, info):
        self.log.append("> %s" % info.path)
        yield next_(root, args, context, info)
        self.log.append("< %s" % info.path)


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
