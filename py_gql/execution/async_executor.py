# -*- coding: utf-8 -*-

import asyncio
import functools as ft
from inspect import isawaitable, iscoroutinefunction
from typing import Any, Callable

from .executor import Executor

Resolver = Callable[..., Any]


class AsyncExecutor(Executor):
    """
    Executor implementation to work Python's asyncio.
    """

    @staticmethod
    async def gather_values(values):
        pending = []
        pending_idx = []
        done = []
        for index, value in enumerate(values):
            if isawaitable(value):
                pending.append(value)
                pending_idx.append(index)
            done.append(value)

        for index, awaited in zip(pending_idx, await asyncio.gather(*pending)):
            done[index] = awaited
        return done

    @staticmethod
    async def map_value(value, then, else_=None):
        try:
            return then(await unwrap_coro(value))
        except Exception as err:
            if else_ and isinstance(err, else_[0]):
                return else_[1](err)
            raise

    @staticmethod
    def unwrap_value(value):
        return unwrap_coro(value)

    def wrap_field_resolver(self, base: Resolver) -> Resolver:
        if not iscoroutinefunction(base):

            async def resolver(*args, **kwargs):
                return await asyncio.get_event_loop().run_in_executor(
                    None, ft.partial(base, *args, **kwargs)
                )

            return resolver

        return base


async def unwrap_coro(maybe_coro):
    if isawaitable(maybe_coro):
        return await unwrap_coro(await maybe_coro)

    return maybe_coro
