# -*- coding: utf-8 -*-
import asyncio
import functools as ft
from inspect import isawaitable, iscoroutinefunction
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .base import SubscriptionRuntime


T = TypeVar("T")
G = TypeVar("G")
E = TypeVar("E", bound=Exception)
AnyFn = Callable[..., Any]
AnyFnGen = Callable[..., T]
MaybeAwaitable = Union[Awaitable[T], T]


class AsyncIORuntime(SubscriptionRuntime):
    """
    Executor implementation to work with Python's asyncio module.
    """

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        execute_blocking_functions_in_thread: bool = True,
    ):
        self.loop = loop or asyncio.get_event_loop()
        self._execute_blocking_functions_in_thread = (
            execute_blocking_functions_in_thread
        )

    def submit(
        self,
        fn: AnyFnGen[T],
        *args: Any,
        **kwargs: Any,
    ) -> MaybeAwaitable[T]:
        if (
            self._execute_blocking_functions_in_thread
            and not iscoroutinefunction(fn)
        ):

            return self.loop.run_in_executor(
                None,
                ft.partial(fn, *args, **kwargs),
            )

        return fn(*args, **kwargs)

    def ensure_wrapped(self, value: MaybeAwaitable[T]) -> Awaitable[T]:
        if _isawaitable_fast(value):
            return value  # type: ignore

        async def _make_awaitable() -> T:
            return value  # type: ignore

        return _make_awaitable()

    def gather_values(
        self,
        values: Iterable[MaybeAwaitable[T]],
    ) -> MaybeAwaitable[Iterable[T]]:

        pending = []  # type: List[Awaitable[T]]
        pending_idx = []  # type: List[int]
        done = []  # type: List[T]

        pending_append = pending.append
        pending_idx_append = pending_idx.append
        done_append = done.append
        has_pending = False

        for index, value in enumerate(values):
            if _isawaitable_fast(value):
                has_pending = True
                pending_append(value)  # type: ignore
                pending_idx_append(index)

            done_append(value)  # type: ignore

        if has_pending:

            async def _await_values() -> Iterable[T]:
                for i, awaited in zip(
                    pending_idx,
                    await asyncio.gather(*pending),
                ):
                    done[i] = awaited
                return done

            return _await_values()

        return done

    def map_value(
        self,
        value: MaybeAwaitable[T],
        then: Callable[[T], G],
        else_: Optional[Tuple[Type[E], Callable[[E], G]]] = None,
    ) -> MaybeAwaitable[G]:

        if _isawaitable_fast(value):

            async def _await_value() -> G:
                try:
                    return then(await value)  # type: ignore
                except Exception as err:
                    if else_ and isinstance(err, else_[0]):
                        return else_[1](err)
                    raise

            return _await_value()

        try:
            return then(value)  # type: ignore
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

    async def map_stream(
        self,
        source_stream: AsyncIterator[T],
        map_value: Callable[[T], Awaitable[G]],
    ) -> AsyncIterable[G]:
        async for value in source_stream:
            yield await map_value(value)

    def wrap_callable(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if (
            self._execute_blocking_functions_in_thread
            and not iscoroutinefunction(func)
        ):

            async def wrapped(*args, **kwargs):
                return await self.loop.run_in_executor(
                    None,
                    ft.partial(func, *args, **kwargs),
                )

            return wrapped

        return func


def _isawaitable_fast(value, cache={}, __isawaitable=isawaitable):
    # This is (usually) faster than the default isawaitable which is benefitial
    # for the hot loops required when resolving large objects.
    # TODO: This has been true in my use cases (mostly using dicts), but it may
    # not be the case for all use cases, e.g. when using Django a lot of
    # different classes may appear for models and this may end up having to drop
    # to isawaitable anyway with the cache miss cost on top. Ideally the number
    # of different classes is an order of magnitude smaller than the number of
    # individual objects involved (at the point where this kind of optimisation
    # matters) but this could do with some proper benchmarking against real life
    # use cases.
    t = type(value)
    try:
        return cache[t]
    except KeyError:
        res = cache[t] = __isawaitable(value)
        return res
