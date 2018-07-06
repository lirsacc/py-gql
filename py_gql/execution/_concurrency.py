# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module in a way similar
to promises """

from concurrent import futures as _f

_UNDEF = object()


def is_deferred(value):
    return isinstance(value, _f.Future)


def deferred(value):
    """ Transform a value into a ``Future`` awaitable object.

    :type value: any
    :param value: Original value

    :rtype: concurrent.futures.Future
    :returns: Value wrapped in a ``Future``

    >>> deferred = deferred(1)
    >>> deferred.result(), deferred.done()
    (1, True)
    """
    future = _f.Future()
    future.set_result(value)
    return future


def ensure_deferred(maybe_future):
    """ Make sure an object is deferred as a ``Future`` if not already.

    :type maybe_future: any
    :param maybe_future: Original value

    :rtype: concurrent.futures.Future
    :returns: Value wrapped in a ``Future`` if not alrady the case
    """
    if isinstance(maybe_future, _f.Future):
        return maybe_future
    return deferred(maybe_future)


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
        return deferred([])

    result = _f.Future()
    results_list = [_UNDEF] * len(futures)

    def cancel_remaining():
        for f in futures:
            f.cancel()

    def callback_for(index):
        def callback(future):

            if result.done():
                return

            if not future.done():
                raise RuntimeError(
                    "Future callback called while future is not done."
                )

            try:
                res = future.result()
            # Also includes the case where ``future`` was cancelled.
            except Exception as err:
                cancel_remaining()
                result.set_exception(err)
            else:
                results_list[index] = res

            if all(x is not _UNDEF for x in results_list):
                result.set_result(results_list)

        return callback

    result.set_running_or_notify_cancel()
    for index, future in enumerate(futures):
        future.add_done_callback(callback_for(index))

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
    result = _f.Future()
    stack = list(funcs)[::-1]

    if callable(leader):
        leader = leader(None)

    def callback(future):
        if not future.done():
            raise RuntimeError(
                "Future callback called while future is not done."
            )

        try:
            res = future.result()
        # Also includes the case where ``future`` was cancelled.
        except Exception as err:
            result.set_exception(err)
        else:
            try:
                func = stack.pop()
            except IndexError:
                result.set_result(res)
            else:
                try:
                    mapped = func(res)
                except Exception as err:
                    result.set_exception(err)
                else:
                    ensure_deferred(mapped).add_done_callback(callback)

    result.set_running_or_notify_cancel()
    ensure_deferred(leader).add_done_callback(callback)
    return result


def unwrap(future):
    """ Resolve nested futures until a non future is resolved or an
    exception is raised.

    :type future: concurrent.futures.Future
    :param future: Future to unwrap

    :rtype: any
    :returns: Unwrapped value
    """
    result = _f.Future()

    def callback(future):
        if not future.done():
            raise RuntimeError(
                "Future callback called while future is not done."
            )

        try:
            res = future.result()
        # Also includes the case where ``future`` was cancelled.
        except Exception as err:
            result.set_exception(err)
        else:
            if isinstance(res, _f.Future):
                res.add_done_callback(callback)
            else:
                result.set_result(res)

    result.set_running_or_notify_cancel()
    future.add_done_callback(callback)
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
        return lambda _: original()  # Need to force a scope change

    return chain(deferred(None), *[_step(step) for step in steps])


def except_(future, exc_cls=(Exception,), map_=lambda x: None):
    """ Except for futures.

    :type future: concurrent.futures.Future
    :param future: Future to wrap

    :type exc_cls: Union[type, Tuple[*type]]
    :param exc_cls: Exception classes to expect.
        Can be any value compatible with a standard ``except`` clause.

    :type map_: Optional[callable]
    :param map_:
        Will be passed the expected exception to generate the wrapped future's
        result.
        Default behaviour is to set the result to ``None``.
    """
    result = _f.Future()

    def callback(future):

        if not future.done():
            raise RuntimeError(
                "Future callback called while future is not done."
            )

        try:
            res = future.result()
        except exc_cls as err:
            result.set_result(map_(err))
        except Exception as err:
            result.set_exception(err)
        else:
            result.set_result(res)

    result.set_running_or_notify_cancel()
    future.add_done_callback(callback)
    return result
