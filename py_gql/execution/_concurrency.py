# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module in a way similar
to promises """

import logging
from concurrent.futures import Future as __Future
import threading

logger = logging.getLogger(__name__)

_UNDEF = object()

_CONDITION = threading.Condition()


# [Hackish] These futures only exist in a single thread, hence they can share
# the condition. Ideally there is a way to completely remove synchronisation for
# these artifical futures.
class SharedLockFuture(__Future):
    def __init__(self):
        self._state = "pending"
        self._result = None
        self._exception = None
        self._waiters = []
        self._done_callbacks = []
        self._condition = _CONDITION


Future = SharedLockFuture


def is_deferred(value, cache={}):  # pylint: disable = dangerous-default-value
    t = value.__class__
    if t not in cache:
        cache[t] = callable(getattr(t, "add_done_callback", None))
    return cache[t]


def deferred(value):
    """ Transform a value into a ``Future`` awaitable object.

    :type value: any
    :param value: Original value

    :rtype: concurrent.futures.Future
    :returns: Value wrapped in a ``Future``

    >>> v = deferred(1)
    >>> v.result(), v.done()
    (1, True)
    """
    future = Future()
    future.set_result(value)
    return future


def all_(futures):
    """ Create a ``concurrent.futures.Future`` wrapping a list of futures.

    - The resulting future resolves only when all futures have resolved.
    - If any future rejects, the wrapping future rejects with the exception for
      that future.
    - The created future does not need an executor is considered running by
      default. As a result it cannot be cancelled, however if any of the inner
      futures is cancelled the ``concurrent.futures.CancelledError`` will be
      considered as an exception and propagated to the resulting future.

    :type futures: List[concurrent.futures.Future]
    :param futures: List of futures.

    :rtype: concurrent.futures.Future
    :returns: Single future
    """

    if not futures:
        return []

    result = Future()
    results_list = [_UNDEF] * len(futures)
    done_count = [0]
    len_ = len(futures)

    def notify():
        if done_count[0] == len_:
            result.set_result(results_list)

    def callback_for(index):
        def callback(future):

            try:
                res = future.result()
            except Exception as err:  # pylint: disable = broad-except
                result.set_exception(err)
            else:
                results_list[index] = res
                done_count[0] += 1
                notify()

        return callback

    for index, future in enumerate(futures):
        if is_deferred(future):
            future.add_done_callback(callback_for(index))
        else:
            results_list[index] = future
            done_count[0] += 1

    if done_count[0] == len_:
        return results_list
    return result


def _chain_one(source_future, map_=lambda x: x):
    result = Future()

    def _callback(future):
        try:
            res = map_(future.result())
        except Exception as err:  # pylint: disable = broad-except
            result.set_exception(err)
        else:
            result.set_result(res)

    source_future.add_done_callback(_callback)
    return result


def chain(leader, *funcs):
    """ Chain future factories together until all steps have been exhausted.

    - Final result can be either a deferred value or not, depends on the return
      type of the last step in chain. Use :func:`unwrap` to ensure the final
      result is not a future.
    - Assumes futures are independantly submitted to an executor in order to
      work without context knowledge.
    - The created future does not need an executor is considered running by
      default. As a result it cannot be cancelled, however if any of the inner
      futures is cancelled the ``concurrent.futures.CancelledError`` will be
      considered as an exception and propagated to the resulting future.

    :type leader: concurrrent.futures.Future
    :param leader: First future in the chain.
        Can be ommitted, in which case the first step will be called with
        ``None`` as input.

    :type funcs: Iterable[(any) -> any]
    :param funcs: Steps in the chain
        Each step receives the result of the previous step as input.
        Return value of a step can be either a future or a value which will be
        wrapped as a future if there is more steps to compute.

    :rtype: concurrent.futures.Future
    """
    stack = iter(funcs)

    def _next(value):
        if is_deferred(value):
            return unwrap(_chain_one(value, _next))
        try:
            func = next(stack)
        except StopIteration:
            return value
        else:
            return _next(func(value))

    return _next(leader)


def unwrap(source_future):
    """ Resolve nested futures until a non future is resolved or an
    exception is raised.

    :type source_future: concurrent.futures.Future
    :param source_future: Future to unwrap

    :rtype: any
    :returns: Unwrapped value
    """
    result = Future()

    def callback(future):
        try:
            res = future.result()
        except Exception as err:  # pylint: disable = broad-except
            result.set_exception(err)
        else:
            if is_deferred(res):
                res.add_done_callback(callback)
            else:
                result.set_result(res)

    source_future.add_done_callback(callback)
    return result


def serial(steps):
    """ Similar to :func:`chain` but ignoring the intermediate results.

    Each step is called only after the result of the previous step has
    resolved. The resulting future rejects on the first step that rejects.

    :type steps: Iterable[() -> concurrent.futures.Future]
    :param steps:

    :rtype: concurrent.futures.Future
    :returns: Wrapped promise
    """

    def _step(original):
        return lambda _: original()

    return chain(None, *[_step(step) for step in steps])


def except_(source_future, exc_cls=(Exception,), map_=lambda x: None):
    """ Except for futures.

    :type source_future: concurrent.futures.Future
    :param source_future: Future to wrap

    :type exc_cls: Union[type, Tuple[*type]]
    :param exc_cls: Exception classes to expect.
        Can be any value compatible with a standard ``except`` clause.

    :type map_: Optional[callable]
    :param map_:
        Will be passed the expected exception to generate the wrapped future's
        result.
        Default behaviour is to set the result to ``None``.
    """
    result = Future()

    def callback(future):
        try:
            res = future.result()
        except exc_cls as err:
            result.set_result(map_(err))
        except Exception as err:  # pylint: disable = broad-except
            result.set_exception(err)
        else:
            result.set_result(res)

    source_future.add_done_callback(callback)
    return result
