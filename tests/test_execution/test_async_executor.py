# -*- coding: utf-8 -*-
"""
Execution tests specific to AsyncIOExecutor.
"""

import asyncio
from typing import Any, Awaitable

import pytest

from py_gql import build_schema
from py_gql.exc import ResolverError
from py_gql.execution import AsyncIOExecutor

from ._test_utils import assert_execution

schema = build_schema(
    """
    type Query {
        a: Int!
        nested: Int!
        sync_a: Int!
        b(sleep: Float): Int!
        c: [Int]!
        error: Int!
        sync_error: Int!
    }
    """
)


@schema.resolver("Query.a")
async def resolve_a(*_: Any) -> int:
    return 42


@schema.resolver("Query.nested")
async def resolve_nested(*_: Any) -> Awaitable[int]:
    return resolve_a()  # type: ignore


@schema.resolver("Query.sync_a")
def resolve_sync_a(*_: Any) -> int:
    return 42


@schema.resolver("Query.b")
async def resolve_b(*_: Any, sleep: float) -> int:
    await asyncio.sleep(sleep)
    return 42


@schema.resolver("Query.error")
async def resolve_error(*_: Any) -> None:
    raise ResolverError("FOO")


@schema.resolver("Query.sync_error")
def resolve_sync_error(*_: Any) -> None:
    raise ResolverError("FOO")


@schema.resolver("Query.c")
async def resolve_c(*_: Any) -> int:
    return 42


@pytest.mark.asyncio
async def test_AsyncIOExecutor_simple_field():
    await assert_execution(
        schema, "{ a }", expected_data={"a": 42}, executor_cls=AsyncIOExecutor
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_nested_awaits():
    await assert_execution(
        schema,
        "{ nested }",
        expected_data={"nested": 42},
        executor_cls=AsyncIOExecutor,
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_simple_sync_field():
    await assert_execution(
        schema,
        "{ sync_a }",
        expected_data={"sync_a": 42},
        executor_cls=AsyncIOExecutor,
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_simple_field_with_io():
    await assert_execution(
        schema,
        "{ b(sleep: 0.001) }",
        expected_data={"b": 42},
        executor_cls=AsyncIOExecutor,
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_field_with_error():
    await assert_execution(
        schema,
        "{ error }",
        expected_data={"error": None},
        expected_errors=[("FOO", (2, 7), "error")],
        executor_cls=AsyncIOExecutor,
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_field_with_sync_error():
    await assert_execution(
        schema,
        "{ sync_error }",
        expected_data={"sync_error": None},
        expected_errors=[("FOO", (2, 12), "sync_error")],
        executor_cls=AsyncIOExecutor,
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_runtime_error():
    with pytest.raises(RuntimeError):
        await assert_execution(schema, "{ c }", executor_cls=AsyncIOExecutor)


@pytest.mark.asyncio
async def test_AsyncIOExecutor_ensure_wrapped_awaitable():
    async def a():
        return 42

    awaitable = a()
    assert AsyncIOExecutor.ensure_wrapped(awaitable) is awaitable
    assert await awaitable == 42


@pytest.mark.asyncio
async def test_AsyncIOExecutor_ensure_wrapped_non_awaitable():
    assert await AsyncIOExecutor.ensure_wrapped(42) == 42


@pytest.mark.asyncio
async def test_AsyncIOExecutor_gather_values_empty_input():
    assert AsyncIOExecutor.gather_values([]) == []


@pytest.mark.asyncio
async def test_AsyncIOExecutor_gather_values_sync_input():
    assert AsyncIOExecutor.gather_values([1, 2, 3]) == [1, 2, 3]


@pytest.mark.asyncio
async def test_AsyncIOExecutor_gather_values_async_input():
    assert await AsyncIOExecutor.gather_values(
        [1, AsyncIOExecutor.ensure_wrapped(2), 3]
    ) == [1, 2, 3]


@pytest.mark.asyncio
async def test_AsyncIOExecutor_gather_values_surfaces_errors():
    def a():
        raise ValueError()

    with pytest.raises(ValueError):
        await AsyncIOExecutor.gather_values([a()])


@pytest.mark.asyncio
async def test_AsyncIOExecutor_map_value_sync_ok():
    assert AsyncIOExecutor.map_value(42, lambda x: x * 2) == 84


@pytest.mark.asyncio
async def test_AsyncIOExecutor_map_value_sync_fail(raiser):
    with pytest.raises(ValueError):
        AsyncIOExecutor.map_value(42, raiser(ValueError))


@pytest.mark.asyncio
async def test_AsyncIOExecutor_map_value_sync_caught(raiser):
    assert (
        AsyncIOExecutor.map_value(
            42, raiser(ValueError), (ValueError, lambda _: 42)
        )
        == 42
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_map_value_async_ok():
    assert (
        await AsyncIOExecutor.map_value(
            AsyncIOExecutor.ensure_wrapped(42), lambda x: x * 2
        )
        == 84
    )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_map_value_async_fail(raiser):
    with pytest.raises(ValueError):
        await AsyncIOExecutor.map_value(
            AsyncIOExecutor.ensure_wrapped(42), raiser(ValueError)
        )


@pytest.mark.asyncio
async def test_AsyncIOExecutor_map_value_async_caught(raiser):
    assert (
        await AsyncIOExecutor.map_value(
            AsyncIOExecutor.ensure_wrapped(42),
            raiser(ValueError),
            (ValueError, lambda _: 42),
        )
        == 42
    )
