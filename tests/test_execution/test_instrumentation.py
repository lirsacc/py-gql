# -*- coding: utf-8 -*-
import pytest

from py_gql.execution import Instrumentation, MultiInstrumentation

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


async def test_instrumentation_does_not_raise(
    assert_execution, starwars_schema
):
    await process_request(
        starwars_schema, QUERY, instrumentation=Instrumentation(),
    )


async def test_multi_instrumentation_stack_ordering(  # noqa: C901
    assert_execution, starwars_schema
):
    class TrackingInstrumentation(Instrumentation):
        def __init__(self, prefix, stack):
            self.prefix = prefix
            self.stack = stack

        def on_query_start(self):
            self.stack.append((">", self.prefix, "query"))

        def on_parsing_start(self):
            self.stack.append((">", self.prefix, "parse"))

        def on_validation_start(self):
            self.stack.append((">", self.prefix, "validate"))

        def on_execution_start(self):
            self.stack.append((">", self.prefix, "execution"))

        def on_field_start(self, _root, _context, info):
            self.stack.append((">", self.prefix, ("field", tuple(info.path))))

        def on_query_end(self):
            self.stack.append(("<", self.prefix, "query"))

        def on_parsing_end(self):
            self.stack.append(("<", self.prefix, "parse"))

        def on_validation_end(self):
            self.stack.append(("<", self.prefix, "validate"))

        def on_execution_end(self):
            self.stack.append(("<", self.prefix, "execution"))

        def on_field_end(self, _root, _context, info):
            self.stack.append(("<", self.prefix, ("field", tuple(info.path))))

    stack = []  # type: ignore

    instrumentation = MultiInstrumentation(
        TrackingInstrumentation("a", stack), TrackingInstrumentation("b", stack)
    )

    await process_request(
        starwars_schema, QUERY, instrumentation=instrumentation,
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
            (">", "a", "validate"),
            (">", "b", "validate"),
            ("<", "b", "validate"),
            ("<", "a", "validate"),
            (">", "a", "execution"),
            (">", "b", "execution"),
            ("<", "b", "execution"),
            ("<", "a", "execution"),
            ("<", "b", "query"),
            ("<", "a", "query"),
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
