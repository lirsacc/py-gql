# -*- coding: utf-8 -*-
import pytest

from py_gql.execution import Instrumentation, MultiInstrumentation
from py_gql.lang import parse

from ._test_utils import process_request

pytestmark = pytest.mark.asyncio


QUERY = """
query {
    hero {
        ... characterFragment
        friends {
            ... characterFragment
        }
    }
}

fragment characterFragment on Character {
    name
}
"""


async def test_instrumentation_does_not_raise(executor_cls, starwars_schema):
    await process_request(
        starwars_schema,
        QUERY,
        executor_cls=executor_cls,
        instrumentation=Instrumentation(),
    )


async def test_instrument_ast(executor_cls, starwars_schema):
    class TestInstrumentation(Instrumentation):
        def instrument_ast(self, _ast):
            return parse("query { hero { name } }")

    result = await process_request(
        starwars_schema,
        QUERY,
        executor_cls=executor_cls,
        instrumentation=TestInstrumentation(),
    )

    assert result.response() == {"data": {"hero": {"name": "R2-D2"}}}


async def test_instrument_result(executor_cls, starwars_schema):
    class TestInstrumentation(Instrumentation):
        def instrument_result(self, result):
            result.data["hero"]["name"] = "Darth Vader"
            return result

    result = await process_request(
        starwars_schema,
        QUERY,
        executor_cls=executor_cls,
        instrumentation=TestInstrumentation(),
    )

    assert result.response() == {
        "data": {
            "hero": {
                "friends": [
                    {"name": "Luke Skywalker"},
                    {"name": "Han Solo"},
                    {"name": "Leia Organa"},
                ],
                "name": "Darth Vader",
            }
        }
    }


async def test_multi_instrumentation_stack_ordering(
    executor_cls, starwars_schema
):
    class TrackingInstrumentation(Instrumentation):
        def __init__(self, prefix, stack):
            self.prefix = prefix
            self.stack = stack

        def track(self, key):
            self.stack.append((">", self.prefix, key))

            def cb():
                self.stack.append(("<", self.prefix, key))

            return cb

        def on_query(self):
            return self.track("query")

        def on_parse(self):
            return self.track("parse")

        def on_validate(self):
            return self.track("validate")

        def on_execution(self):
            return self.track("execution")

        def on_field(self, _root, _context, info):
            return self.track(("field", tuple(info.path)))

        def instrument_ast(self, ast):
            self.track("instrument_ast")
            return ast

        def instrument_validation_result(self, result):
            self.track("instrument_validation_result")
            return result

        def instrument_result(self, result):
            self.track("instrument_result")
            return result

    stack = []  # type: ignore

    instrumentation = MultiInstrumentation(
        TrackingInstrumentation("a", stack), TrackingInstrumentation("b", stack)
    )

    await process_request(
        starwars_schema,
        QUERY,
        executor_cls=executor_cls,
        instrumentation=instrumentation,
    )

    # Non blocking executor could lead to different ordering across fields so
    # we only check that tracking a specific stage leads to correct ordering but
    # not absolute ordering of all stages.
    def assert_ordered_subset_in_stack(expected_subset):
        filtered = [entry for entry in stack if entry in expected_subset]
        assert expected_subset == filtered

    assert_ordered_subset_in_stack(
        [
            (">", "a", "query"),
            (">", "b", "query"),
            (">", "a", "parse"),
            (">", "b", "parse"),
            ("<", "b", "parse"),
            ("<", "a", "parse"),
            (">", "a", "instrument_ast"),
            (">", "b", "instrument_ast"),
            (">", "a", "validate"),
            (">", "b", "validate"),
            ("<", "b", "validate"),
            ("<", "a", "validate"),
            (">", "a", "instrument_validation_result"),
            (">", "b", "instrument_validation_result"),
            (">", "a", "execution"),
            (">", "b", "execution"),
            ("<", "b", "execution"),
            ("<", "a", "execution"),
            ("<", "b", "query"),
            ("<", "a", "query"),
            (">", "a", "instrument_result"),
            (">", "b", "instrument_result"),
        ]
    )

    assert_ordered_subset_in_stack(
        [
            (">", "a", ("field", ("hero",))),
            (">", "b", ("field", ("hero",))),
            ("<", "b", ("field", ("hero",))),
            ("<", "a", ("field", ("hero",))),
        ]
    )

    assert_ordered_subset_in_stack(
        [
            (">", "a", ("field", ("hero", "name"))),
            (">", "b", ("field", ("hero", "name"))),
            ("<", "b", ("field", ("hero", "name"))),
            ("<", "a", ("field", ("hero", "name"))),
        ]
    )

    assert_ordered_subset_in_stack(
        [
            (">", "a", ("field", ("hero", "friends"))),
            (">", "b", ("field", ("hero", "friends"))),
            ("<", "b", ("field", ("hero", "friends"))),
            ("<", "a", ("field", ("hero", "friends"))),
        ]
    )

    assert_ordered_subset_in_stack(
        [
            (">", "a", ("field", ("hero", "friends", 0, "name"))),
            (">", "b", ("field", ("hero", "friends", 0, "name"))),
            ("<", "b", ("field", ("hero", "friends", 0, "name"))),
            ("<", "a", ("field", ("hero", "friends", 0, "name"))),
        ]
    )

    assert_ordered_subset_in_stack(
        [
            (">", "a", ("field", ("hero", "friends", 1, "name"))),
            (">", "b", ("field", ("hero", "friends", 1, "name"))),
            ("<", "b", ("field", ("hero", "friends", 1, "name"))),
            ("<", "a", ("field", ("hero", "friends", 1, "name"))),
        ]
    )

    assert_ordered_subset_in_stack(
        [
            (">", "a", ("field", ("hero", "friends", 2, "name"))),
            (">", "b", ("field", ("hero", "friends", 2, "name"))),
            ("<", "b", ("field", ("hero", "friends", 2, "name"))),
            ("<", "a", ("field", ("hero", "friends", 2, "name"))),
        ]
    )
