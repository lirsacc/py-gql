# -*- coding: utf-8 -*-
"""
"""

import asyncio
import functools as ft
from inspect import isawaitable, iscoroutinefunction
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Optional,
    TypeVar,
)

from .base import SubscriptionEnabledRuntime

Resolver = Callable[..., Any]
T = TypeVar("T")
G = TypeVar("G")


class AsyncIORuntime(SubscriptionEnabledRuntime):
    """
    Executor implementation to work Python's asyncio.
    """

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        execute_blocking_resolvers_in_thread: bool = True,
    ):
        self.loop = loop or asyncio.get_event_loop()
        self._execute_blocking_resolvers_in_thread = (
            execute_blocking_resolvers_in_thread
        )

    def ensure_wrapped(self, value):
        if _isawaitable_fast(value):
            return value

        async def _make_awaitable():
            return value

        return _make_awaitable()

    def gather_values(self, values):

        pending = []  # type: ignore
        pending_idx = []  # type: ignore
        done = []  # type: ignore

        pending_append = pending.append
        pending_idx_append = pending_idx.append
        done_append = done.append
        has_pending = False

        for index, value in enumerate(values):
            if _isawaitable_fast(value):
                has_pending = True
                pending_append(value)
                pending_idx_append(index)

            done_append(value)

        if has_pending:

            async def _await_values():
                for i, awaited in zip(
                    pending_idx, await asyncio.gather(*pending)
                ):
                    done[i] = awaited
                return done

            return _await_values()

        return done

    def map_value(self, value, then, else_=None):

        if _isawaitable_fast(value):

            async def _await_value():
                try:
                    return then(await value)
                except Exception as err:
                    if else_ and isinstance(err, else_[0]):
                        return else_[1](err)
                    raise

            return _await_value()

        try:
            return then(value)
        except Exception as err:
            if else_ and isinstance(err, else_[0]):
                return else_[1](err)
            raise

    def unwrap_value(self, value):
        if _isawaitable_fast(value):

            async def _await_value():
                cur = await value
                while _isawaitable_fast(cur):
                    cur = await cur

                return cur

            return _await_value()

        return value

    def map_stream(
        self,
        source_stream: AsyncIterator[T],
        map_value: Callable[[T], Awaitable[G]],
    ) -> AsyncIterable[G]:
        return AsyncMap(source_stream, map_value)

    def wrap_callable(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if (
            self._execute_blocking_resolvers_in_thread
            and not iscoroutinefunction(func)
        ):

            async def wrapped(*args, **kwargs):
                return await self.loop.run_in_executor(
                    None, ft.partial(func, *args, **kwargs)
                )

            return wrapped

        return func


# We cannot use async generators in order to support Python 3.5.
class AsyncMap:
    __slots__ = ("source_stream", "map_value")

    def __init__(self, source_stream, map_value):
        self.source_stream = source_stream
        self.map_value = map_value

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.map_value(
            await type(self.source_stream).__anext__(self.source_stream)
        )


def _isawaitable_fast(value, cache={}, __isawaitable=isawaitable):
    # This is faster than the default isawaitable which is benefitial for the
    # hot loops required when resolving large objects.
    t = type(value)
    try:
        return cache[t]
    except KeyError:
        res = cache[t] = __isawaitable(value)
        return res
