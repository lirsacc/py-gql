# -*- coding: utf-8 -*-

# REVIEW: This is likely suboptimal and create too many wrapping Future
# instances.

import functools
from concurrent.futures import (
    CancelledError,
    Future,
    ThreadPoolExecutor as _ThreadPoolExecutor,
)
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

from .executor import Executor

T = TypeVar("T")
G = TypeVar("G")
E = TypeVar("E", bound=Exception)

MaybeFuture = Union["Future[T]", T]
Resolver = Callable[..., Any]


class ThreadPoolExecutor(Executor):
    @staticmethod
    def map_value(value, then, else_=None):
        return chain(unwrap_future(value), then, else_)

    @staticmethod
    def gather_values(values):
        return gather_futures(values)

    @staticmethod
    def unwrap_value(value):
        return unwrap_future(value)

    __slots__ = Executor.__slots__ + ("_inner",)

    def __init__(
        # fmt: off
        self,
        *args: Any,
        inner_executor: Optional[_ThreadPoolExecutor] = None,
        **kwargs: Any
        # fmt: on
    ):
        super().__init__(*args, **kwargs)
        self._inner = inner_executor or _ThreadPoolExecutor()

    def wrap_field_resolver(self, resolver: Resolver) -> Resolver:
        return functools.partial(self._inner.submit, resolver)


def unwrap_future(maybe_future):
    outer = Future()  # type: ignore
    if isinstance(maybe_future, Future):

        def cb(f):
            try:
                r = f.result()
            except CancelledError:
                outer.cancel()
            # pylint: disable = broad-except
            except Exception as err:
                outer.set_exception(err)
            else:
                if isinstance(r, Future):
                    r.add_done_callback(cb)
                else:
                    outer.set_result(r)

        maybe_future.add_done_callback(cb)
    else:
        outer.set_result(maybe_future)

    return outer


def gather_futures(source: Iterable[MaybeFuture[T]]) -> "Future[List[T]]":
    """ Concurrently collect multiple Futures. This is based on `asyncio.gather`.

    If all futures in the ``source`` sequence complete successfully, the result
    is an aggregate list of returned values. The order of result values
    corresponds to the order of the provided futures.

    The first raised exception is immediately propagated to the future returned
    from ``gather_futures()``. Other futures in the provided sequence won’t be
    cancelled and will continue to run.

    Cancelling ``gather_futures()`` will attempt to cancel the source futures
    that haven't already completed. If any Future from the ``source`` sequence
    is cancelled, it is treated as if it raised `CancelledError` – the
    ``gather_futures()`` call is not cancelled in this case. This is to prevent the
    cancellation of one submitted Future to cause other futures to be
    cancelled.
    """
    done = 0
    pending = []  # type: List[Future[T]]
    result = []  # type: List[MaybeFuture[T]]

    source_values = list(source)
    target_count = len(source_values)

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
        # pylint: disable = broad-except
        except Exception as err:
            outer.set_exception(err)
            return

        if done == target_count:
            res = [v.result() if isinstance(v, Future) else v for v in result]
            outer.set_result(res)

    outer = Future()  # type: Future[List[T]]
    outer.add_done_callback(handle_cancel)

    for maybe_future in source_values:
        if not isinstance(maybe_future, Future):
            result.append(maybe_future)
            done += 1
        else:
            pending.append(maybe_future)
            result.append(maybe_future)
            maybe_future.add_done_callback(on_finish)

    if target_count == 0:
        outer.set_result([])
    elif not pending:
        outer.set_result(cast(List[T], result))

    return outer


def chain(
    source: "Future[T]",
    then: Callable[[T], G],
    else_: Optional[
        Tuple[Union[Type[E], Tuple[Type[E], ...]], Callable[[E], G]]
    ] = None,
) -> "Future[G]":
    target = Future()  # type: Future[G]

    def on_finish(f: "Future[T]") -> None:
        try:
            res = then(f.result())
        except CancelledError:
            target.cancel()
        # pylint: disable = broad-except
        except Exception as err:
            if else_ is not None:
                exc_type, cb = else_
                if isinstance(err, exc_type):
                    target.set_result(cb(err))  # type: ignore
                else:
                    target.set_exception(err)
            else:
                target.set_exception(err)
        else:
            target.set_result(res)

    source.add_done_callback(on_finish)

    return target
