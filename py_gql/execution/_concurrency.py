# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module in a way similar
to promises """

from concurrent.futures import Future

_UNDEF = object()


def is_deferred(value, cache={}):  # pylint: disable = dangerous-default-value
    t = value.__class__
    if t not in cache:
        cache[t] = callable(getattr(t, "add_done_callback", None))
    return cache[t]


def deferred(value, cls=Future):
    """ Transform a value into a ``Future`` awaitable object.

    >>> v = deferred(1, cls=DummyFuture)
    >>> v.result(), v.done()
    (1, True)
    """
    future = cls()
    future.set_result(value)
    return future


def all_(futures, cls=Future):
    """ Create a ``concurrent.futures.Future`` wrapping a list of futures.

    - The resulting future resolves only when all futures have resolved.
    - If any future rejects, the wrapping future rejects with the exception for
      that future.
    - The created future does not need an executor is considered running by
      default. As a result it cannot be cancelled, however if any of the inner
      futures is cancelled the ``concurrent.futures.CancelledError`` will be
      considered as an exception and propagated to the resulting future.

    Args:
        futures (List[any]): List of potential futures to wrap
        cls: Future class to use for the result

    Returns:
        concurrent.futures.Future: Wrapped future
    """

    if not futures:
        return []

    result = cls()
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


def _chain_one(source_future, map_=lambda x: x, cls=Future):
    result = cls()

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

    Args:
        leader (concurrrent.futures.Future) First future in the chain.
            Can be ommitted, in which case the first step will be called with
            ``None`` as input.
        funcs (Iterable[(any) -> any]): Steps in the chain
            Each step receives the result of the previous step as input.
            Return value of a step can be either a future or a value which will
            be wrapped as a future if there is more steps to compute.
        cls: Future class to use for the result

    Returns:
        concurrent.futures.Future: Wrapped future
    """
    stack = iter(funcs)
    cls = kwargs.get("cls", Future)

    def _next(value):
        if is_deferred(value):
            return unwrap(_chain_one(value, _next, cls=cls), cls=cls)
        try:
            func = next(stack)
        except StopIteration:
            return value
        else:
            return _next(func(value))

    return _next(leader)


def unwrap(source_future, cls=Future):
    """ Resolve nested futures until a non future is resolved or an
    exception is raised.

    Args:
        source_future (concurrent.futures.Future): Future to wrap
        cls: Future class to use for the result

    Returns:
        concurrent.futures.Future: Wrapped future
    """
    if not is_deferred(source_future):
        return deferred(source_future, cls=Future)

    result = cls()

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


def serial(steps, cls=Future):
    """ Similar to :func:`chain` but ignoring the intermediate results.

    Each step is called only after the result of the previous step has
    resolved. The resulting future rejects on the first step that rejects.

    Args:
        steps (Iterable[() -> concurrent.futures.Future]):
        cls: Future class to use for the result

    Returns:
        concurrent.futures.Future: Wrapped future
    """

    def _step(original):
        return lambda _: original()

    return chain(None, *[_step(step) for step in steps], cls=cls)


def except_(
    source_future, exc_cls=(Exception,), map_=lambda x: None, cls=Future
):
    """ Except for futures.

    Args:
        source_future (concurrent.futures.Future): Future to wrap
        exc_cls: Exception to catch, same type as when using ``except``
        map_ (Callable): Called on the caught exception to generate the final
            result. Default behaviour is to set the result to ``None``.
        cls: Future class to use for the result

    Returns:
        concurrent.futures.Future: Wrapped future
    """
    result = cls()

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


class DummyFuture(Future):
    """ Dummy Future to match the interface in a synchronous & single
    threaded environment without the synchronisation overhead. """

    __slots__ = "_result", "_exception", "_callbacks", "_done"

    # pylint: disable = super-init-not-called
    def __init__(self):
        self._done = False
        self._result = None
        self._exception = None
        self._callbacks = []

    def _invoke_callbacks(self):
        for callback in self._callbacks:
            callback(self)

    def __repr__(self):
        if self._done:
            if self._exception:
                return "<%s at %#x state=FINISHED raised %s>" % (
                    self.__class__.__name__,
                    id(self),
                    self._exception.__class__.__name__,
                )
            else:
                return "<%s at %#x state=FINISHED returned %s>" % (
                    self.__class__.__name__,
                    id(self),
                    self._result.__class__.__name__,
                )
        return "<%s at %#x state=RUNNING>" % (self.__class__.__name__, id(self))

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def running(self):
        return not self._done

    def done(self):
        return self._done

    def add_done_callback(self, fn):
        if not self._done:
            self._callbacks.append(fn)
        else:
            fn(self)

    def result(self, timeout=None):
        if not self._done:
            raise RuntimeError(
                "DummyFuture does not support blocking for results"
            )

        if self._exception:
            raise self._exception  # pylint:disable=raising-bad-type
        else:
            return self._result

    def exception(self, timeout=None):
        if not self._done:
            raise RuntimeError(
                "DummyFuture does not support blocking for results"
            )

        if self._exception:
            return self._exception
        else:
            return None

    def set_running_or_notify_cancel(self):
        pass

    def set_result(self, result):
        self._result = result
        self._done = True
        self._invoke_callbacks()

    def set_exception(self, exception):
        self._exception = exception
        self._done = True
        self._invoke_callbacks()
