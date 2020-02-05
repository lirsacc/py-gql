# -*- coding: utf-8 -*-
"""
Execution tests specific to AsyncIORuntime().
"""

import asyncio
from typing import Any, Awaitable, cast

import pytest

from py_gql import build_schema
from py_gql.exc import ResolverError
from py_gql.execution.runtime import AsyncIORuntime

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
    return resolve_a()


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
async def test_AsyncIORuntime_simple_field():
    await assert_execution(
        schema, "{ a }", expected_data={"a": 42}, runtime=AsyncIORuntime()
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_nested_awaits():
    await assert_execution(
        schema,
        "{ nested }",
        expected_data={"nested": 42},
        runtime=AsyncIORuntime(),
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_simple_sync_field():
    await assert_execution(
        schema,
        "{ sync_a }",
        expected_data={"sync_a": 42},
        runtime=AsyncIORuntime(),
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_simple_field_with_io():
    await assert_execution(
        schema,
        "{ b(sleep: 0.001) }",
        expected_data={"b": 42},
        runtime=AsyncIORuntime(),
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_field_with_error():
    await assert_execution(
        schema,
        "{ error }",
        expected_data={"error": None},
        expected_errors=[("FOO", (2, 7), "error")],
        runtime=AsyncIORuntime(),
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_field_with_sync_error():
    await assert_execution(
        schema,
        "{ sync_error }",
        expected_data={"sync_error": None},
        expected_errors=[("FOO", (2, 12), "sync_error")],
        runtime=AsyncIORuntime(),
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_runtime_error():
    with pytest.raises(RuntimeError):
        await assert_execution(schema, "{ c }", runtime=AsyncIORuntime())


@pytest.mark.asyncio
async def test_AsyncIORuntime_ensure_wrapped_awaitable():
    async def a():
        return 42

    awaitable = a()
    assert AsyncIORuntime().ensure_wrapped(awaitable) is awaitable
    assert await awaitable == 42


@pytest.mark.asyncio
async def test_AsyncIORuntime_ensure_wrapped_non_awaitable():
    assert await AsyncIORuntime().ensure_wrapped(42) == 42


@pytest.mark.asyncio
async def test_AsyncIORuntime_gather_values_empty_input():
    assert AsyncIORuntime().gather_values([]) == []


@pytest.mark.asyncio
async def test_AsyncIORuntime_gather_values_sync_input():
    assert AsyncIORuntime().gather_values([1, 2, 3]) == [1, 2, 3]


@pytest.mark.asyncio
async def test_AsyncIORuntime_gather_values_async_input():
    assert await cast(
        Awaitable[int],
        AsyncIORuntime().gather_values(
            [1, AsyncIORuntime().ensure_wrapped(2), 3]
        ),
    ) == [1, 2, 3]


@pytest.mark.asyncio
async def test_AsyncIORuntime_gather_values_surfaces_errors():
    def a():
        raise ValueError()

    with pytest.raises(ValueError):
        AsyncIORuntime().gather_values([a()])


@pytest.mark.asyncio
async def test_AsyncIORuntime_map_value_sync_ok():
    assert AsyncIORuntime().map_value(42, lambda x: x * 2) == 84


@pytest.mark.asyncio
async def test_AsyncIORuntime_map_value_sync_fail(raiser):
    with pytest.raises(ValueError):
        AsyncIORuntime().map_value(42, raiser(ValueError))


@pytest.mark.asyncio
async def test_AsyncIORuntime_map_value_sync_caught(raiser):
    assert (
        AsyncIORuntime().map_value(
            42, raiser(ValueError), (ValueError, lambda _: 42)
        )
        == 42
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_map_value_async_ok():
    def cb(x: int) -> int:
        return x * 2

    assert (
        await cast(
            Awaitable[int],
            AsyncIORuntime().map_value(AsyncIORuntime().ensure_wrapped(42), cb),
        )
        == 84
    )


@pytest.mark.asyncio
async def test_AsyncIORuntime_map_value_async_fail(raiser):
    with pytest.raises(ValueError):
        await AsyncIORuntime().map_value(
            AsyncIORuntime().ensure_wrapped(42), raiser(ValueError)
        )


@pytest.mark.asyncio
async def test_AsyncIORuntime_map_value_async_caught(raiser):
    assert (
        await AsyncIORuntime().map_value(
            AsyncIORuntime().ensure_wrapped(42),
            raiser(ValueError),
            (ValueError, lambda _: 42),
        )
        == 42
    )
