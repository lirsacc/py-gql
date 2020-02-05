# -*- coding: utf-8 -*-

import asyncio

import pytest

from py_gql.exc import ExecutionError, ResolverError
from py_gql.execution import subscribe
from py_gql.execution.runtime import AsyncIORuntime, BlockingRuntime
from py_gql.lang import parse
from py_gql.schema import (
    Argument,
    Field,
    Float,
    Int,
    NonNullType,
    ObjectType,
    Schema,
)


def subscription_schema(field):
    return Schema(
        query_type=ObjectType("Query", [Field("_", Int)]),  # required.
        subscription_type=ObjectType("Subscription", [field]),
    )


# Python 3.5 does not support async for in comprehensions
async def collect_async_iterator(async_iter):
    c = []
    async for x in async_iter:
        c.append(x)
    return c


class AsyncCounter:
    def __init__(self, delay, max_value):
        self.delay = delay
        self.max_value = max_value
        self.value = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.value == self.max_value:
            raise StopAsyncIteration()

        await asyncio.sleep(self.delay)
        self.value += 1
        return self.value


@pytest.mark.asyncio
async def test_raises_on_unsupported_runtime():
    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            subscription_resolver=lambda *_, delay: AsyncCounter(delay, 10),
            resolver=lambda event, *_, **__: event,
        )
    )

    with pytest.raises(RuntimeError):
        subscribe(
            schema,
            parse("subscription { counter(delay: 0.001) }"),
            runtime=BlockingRuntime(),  # type: ignore
        )


@pytest.mark.asyncio
async def test_raises_on_unsupported_operations(starwars_schema):
    with pytest.raises(RuntimeError):
        subscribe(
            starwars_schema,
            parse("query { counter(delay: 0.001) }"),
            runtime=AsyncIORuntime(),
        )


@pytest.mark.asyncio
async def test_raises_on_multiple_fields(starwars_schema):
    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            subscription_resolver=lambda *_, delay: AsyncCounter(delay, 10),
            resolver=lambda event, *_, **__: event,
        )
    )

    with pytest.raises(ExecutionError):
        subscribe(
            schema,
            parse(
                "subscription { counter(delay: 0.001), other: counter(delay: 0.001) }"
            ),
            runtime=AsyncIORuntime(),
        )


@pytest.mark.asyncio
async def test_raises_on_invalid_fields(starwars_schema):
    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            subscription_resolver=lambda *_, delay: AsyncCounter(delay, 10),
            resolver=lambda event, *_, **__: event,
        )
    )

    with pytest.raises(RuntimeError):
        subscribe(
            schema,
            parse("subscription { counter_foo(delay: 0.001) }"),
            runtime=AsyncIORuntime(),
        )


@pytest.mark.asyncio
async def test_raises_on_missing_subscription_resolver(starwars_schema):
    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            resolver=lambda event, *_, **__: event,
        )
    )

    with pytest.raises(RuntimeError):
        subscribe(
            schema,
            parse("subscription { counter(delay: 0.001) }"),
            runtime=AsyncIORuntime(),
        )


@pytest.mark.asyncio
async def test_simple_counter_subscription():
    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            resolver=lambda event, *_, **__: event,
        )
    )

    @schema.subscription("Subscription.counter")
    def counter_subscription(*_, delay):
        return AsyncCounter(delay, 10)

    response_stream = await subscribe(
        schema,
        parse("subscription { counter(delay: 0.001) }"),
        runtime=AsyncIORuntime(),
    )

    assert [{"data": {"counter": x}} for x in range(1, 11)] == [
        r.response() for r in await collect_async_iterator(response_stream)
    ]


@pytest.mark.asyncio
async def test_async_subscription_resolver():
    async def subscription_resolver(*_, delay):
        await asyncio.sleep(delay)
        return AsyncCounter(delay, 10)

    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            subscription_resolver=subscription_resolver,
            resolver=lambda event, *_, **__: event,
        )
    )

    response_stream = await subscribe(
        schema,
        parse("subscription { counter(delay: 0.001) }"),
        runtime=AsyncIORuntime(),
    )

    assert [{"data": {"counter": x}} for x in range(1, 11)] == [
        r.response() for r in await collect_async_iterator(response_stream)
    ]


@pytest.mark.asyncio
async def test_simple_counter_subscription_with_error():
    def resolver(event, *_, **__):
        if event % 2:
            raise ResolverError("I don't like odd numbers.")
        return event

    schema = subscription_schema(
        Field(
            "counter",
            NonNullType(Int),
            args=[Argument("delay", NonNullType(Float))],
            subscription_resolver=lambda *_, delay: AsyncCounter(delay, 10),
            resolver=resolver,
        )
    )

    response_stream = await subscribe(
        schema,
        parse("subscription { counter(delay: 0.001) }"),
        runtime=AsyncIORuntime(),
    )

    assert [
        (
            {"data": {"counter": x}}
            if not x % 2
            else (
                {
                    "data": {"counter": None},  # type: ignore
                    "errors": [  # type: ignore
                        {
                            "locations": [{"column": 16, "line": 1}],
                            "message": "I don't like odd numbers.",
                            "path": ["counter"],
                        }
                    ],
                }
            )
        )
        for x in range(1, 11)
    ] == [r.response() for r in await collect_async_iterator(response_stream)]
