# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module in a way similar
to promises """

import logging
from concurrent.futures import CancelledError, Future

logger = logging.getLogger(__name__)

_UNDEF = object()


def is_deferred(value, cache={}):  # pylint: disable = dangerous-default-value
    t = value.__class__
    if t not in cache:
        cache[t] = callable(getattr(t, "add_done_callback", None))
    return cache[t]


def deferred(value, factory=Future):
    """ Transform a value into a ``Future`` awaitable object.

    :type value: any
    :param value: Original value

    :rtype: concurrent.futures.Future
    :returns: Value wrapped in a ``Future``

    >>> v = deferred(1)
    >>> v.result(), v.done()
    (1, True)
    """
    future = factory()
    future.set_result(value)
    return future


def all_(futures, factory=Future):
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

    result = factory()
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


def _chain_one(source_future, map_=lambda x: x, factory=Future):
    result = factory()

    def _callback(future):
        try:
            res = map_(future.result())
        except Exception as err:  # pylint: disable = broad-except
            result.set_exception(err)
        else:
            result.set_result(res)

    source_future.add_done_callback(_callback)
    return result


def chain(leader, *funcs, **kwargs):
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
    factory = kwargs.get("factory", Future)

    def _next(value):
        if is_deferred(value):
            return unwrap(
                _chain_one(value, _next, factory=factory), factory=factory
            )
        try:
            func = next(stack)
        except StopIteration:
            return value
        else:
            return _next(func(value))

    return _next(leader)


def unwrap(source_future, factory=Future):
    """ Resolve nested futures until a non future is resolved or an
    exception is raised.

    :type source_future: concurrent.futures.Future
    :param source_future: Future to unwrap

    :rtype: any
    :returns: Unwrapped value
    """
    result = factory()

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


def serial(steps, factory=Future):
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

    return chain(None, *[_step(step) for step in steps], factory=factory)


def except_(
    source_future, exc_cls=(Exception,), map_=lambda x: None, factory=Future
):
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
    result = factory()

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


PENDING = "PENDING"
RUNNING = "RUNNING"
CANCELLED = "CANCELLED"
FINISHED = "FINISHED"
DONE = (CANCELLED, FINISHED)


class DummyFuture(object):
    """ Dummy Future to match the interface in a synchronous & single
    threaded environment without the synchronisation overhead. """

    __slots__ = "_state", "_result", "_exception", "_callbacks"

    def __init__(self):
        self._state = PENDING
        self._result = None
        self._exception = None
        self._callbacks = []

    def _invoke_callbacks(self):
        for callback in self._callbacks:
            callback(self)

    def __repr__(self):
        if self._state == FINISHED:
            if self._exception:
                return "<%s at %#x state=%s raised %s>" % (
                    self.__class__.__name__,
                    id(self),
                    self._state.lower(),
                    self._exception.__class__.__name__,
                )
            else:
                return "<%s at %#x state=%s returned %s>" % (
                    self.__class__.__name__,
                    id(self),
                    self._state.lower(),
                    self._result.__class__.__name__,
                )
        return "<%s at %#x state=%s>" % (
            self.__class__.__name__,
            id(self),
            self._state.lower(),
        )

    def cancel(self):
        if self._state in (RUNNING, FINISHED):
            return False

        if self._state == CANCELLED:
            return True

        self._state = CANCELLED
        self._invoke_callbacks()
        return True

    def cancelled(self):
        return self._state == CANCELLED

    def running(self):
        return self._state == RUNNING

    def done(self):
        return self._state in DONE

    def __get_result(self):
        if self._exception:
            # Inference fails
            # pylint: disable = raising-bad-type
            raise self._exception
        else:
            return self._result

    def add_done_callback(self, fn):
        if self._state not in DONE:
            self._callbacks.append(fn)
        else:
            fn(self)

    def result(self, timeout=None):
        if self._state == CANCELLED:
            raise CancelledError()
        elif self._state == FINISHED:
            return self.__get_result()

    def exception(self, timeout=None):
        if self._state == CANCELLED:
            raise CancelledError()
        elif self._state == FINISHED:
            return self._exception

    def set_running_or_notify_cancel(self):
        pass

    def set_result(self, result):
        self._result = result
        self._state = FINISHED
        self._invoke_callbacks()

    def set_exception(self, exception):
        self._exception = exception
        self._state = FINISHED
        self._invoke_callbacks()
