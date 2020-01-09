# -*- coding: utf-8 -*-

import functools
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from .base import Runtime

T = TypeVar("T")
G = TypeVar("G")
E = TypeVar("E", bound=Exception)
MaybeFuture = Union["Future[T]", T]


class ThreadPoolRuntime(Runtime):
    """Runtime implementation which executes every function passed to it in a
    thread pool by wrapping :py:class:`concurrent.futures.ThreadPoolExecutor`.

    All init arguments will be forwarded to
    :py:class:`concurrent.futures.ThreadPoolExecutor`.
    """

    def __init__(self, *args, **kwargs):
        self._inner = ThreadPoolExecutor(*args, **kwargs)

    def submit(self, func, *args, **kwargs):
        return self._inner.submit(func, *args, **kwargs)

    def ensure_wrapped(self, value):
        if _is_future_fast(value):
            return value

        outer = Future()  # type: ignore
        outer.set_result(value)
        return outer

    def map_value(self, value, then, else_=None):
        return chain(value, then, else_)

    def gather_values(self, values):
        return gather_futures(values)

    def unwrap_value(self, value):
        return unwrap_future(value)

    def wrap_callable(self, func):
        return functools.partial(self._inner.submit, func)


def _is_future_fast(value, cache={}, __isinstance=isinstance, __future=Future):
    t = type(value)
    try:
        return cache[t]
    except KeyError:
        res = cache[t] = __isinstance(value, __future)
        return res


def unwrap_future(maybe_future):
    if _is_future_fast(maybe_future):

        outer = Future()  # type: ignore

        def cb(f):
            try:
                r = f.result()
            except CancelledError:
                outer.cancel()
            except Exception as err:
                outer.set_exception(err)
            else:
                if _is_future_fast(r):
                    r.add_done_callback(cb)
                else:
                    outer.set_result(r)

        maybe_future.add_done_callback(cb)
        return outer

    return maybe_future


def gather_futures(source: Iterable[MaybeFuture[T]]) -> "MaybeFuture[List[T]]":
    """Concurrently collect multiple Futures. This is based on `asyncio.gather`.

    If all futures in the ``source`` sequence complete successfully, the result
    is an aggregate list of returned values. The order of result values
    corresponds to the order of the provided futures.

    The first raised exception is immediately propagated to the future returned
    from ``gather_futures()``. Other futures in the provided sequence won’t be
    cancelled and will continue to run.

    Cancelling ``gather_futures()`` will attempt to cancel the source futures
    that haven't already completed. If any Future from the ``source`` sequence
    is cancelled, it is treated as if it raised `CancelledError` – the
    ``gather_futures()`` call is not cancelled in this case. This is to prevent
    the cancellation of one submitted Future to cause other futures to be
    cancelled.
    """
    done = 0
    pending = []  # type: List[Future[T]]
    result = []  # type: List[MaybeFuture[T]]

    pending_append = pending.append
    result_append = result.append

    source_values = list(source)
    target_count = len(source_values)

    for maybe_future in source_values:
        if not _is_future_fast(maybe_future):
            result_append(maybe_future)
            done += 1
        else:
            pending_append(cast("Future[T]", maybe_future))
            result_append(maybe_future)

    if target_count == 0:
        return []

    if not pending:
        return cast(List[T], result)

    # TODO: This is not used internally and is mostly here for completeness
    # but we could drop it.
    def handle_cancel(d: "Future[List[T]]") -> Any:
        if d.cancelled():
            for inner in pending:
                inner.cancel()

    def on_finish(d: "Future[T]") -> Any:
        nonlocal done
        done += 1

        try:
            d.result()
        except Exception as err:
            outer.set_exception(err)
            return

        if done == target_count:
            outer.set_result(
                cast(
                    "List[T]",
                    [
                        cast("Future[T]", v).result()
                        if _is_future_fast(v)
                        else v
                        for v in result
                    ],
                )
            )

    outer = Future()  # type: Future[List[T]]
    outer.add_done_callback(handle_cancel)

    for f in pending:
        f.add_done_callback(on_finish)

    return outer


def chain(
    source: "MaybeFuture[T]",
    then: Callable[[T], G],
    else_: Optional[Tuple[Type[E], Callable[[E], G]]] = None,
) -> "MaybeFuture[G]":

    if not _is_future_fast(source):
        try:
            res = then(cast(T, source))
        except Exception as err:
            if else_ is not None:
                exc_type, cb = else_
                if isinstance(err, exc_type):
                    return cb(err)
            raise
        else:
            return res
    else:

        target = Future()  # type: Future[G]

        def on_finish(f: "Future[T]") -> None:
            try:
                res = then(f.result())
            except CancelledError:
                target.cancel()
            except Exception as err:
                if else_ is not None:
                    exc_type, cb = else_
                    if isinstance(err, exc_type):
                        target.set_result(cb(err))
                    else:
                        target.set_exception(err)
                else:
                    target.set_exception(err)
            else:
                target.set_result(res)

        cast("Future[T]", source).add_done_callback(on_finish)

        return target
