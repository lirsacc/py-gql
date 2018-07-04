# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module in a way similar
to promises """

# TODO: Review this package code. The various `deferred(None)` leaders
# smell .

from concurrent import futures as _f


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
    """ Create a Future from a list of futures that resolves only when all
    futures have resolved.

    If any future rejects, the wrapping future rejects with the exception for
    that future.

    :type futures: List[concurrent.futures.Future]
    :param futures: List of futures.

    :rtype: concurrent.futures.Future
    :returns: Single future

    >>> futures = [_f.Future() for _ in range(10)]
    >>> lst = all_(futures)
    >>> for i, f in enumerate(futures):
    ...     f.set_result(i)
    >>> lst.result()
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    """

    if not futures:
        return deferred([])

    result = _f.Future()
    _undef = object()
    results_list = [_undef] * len(futures)

    def cancel_remaining():
        for f in futures:
            f.cancel()

    def callback_for(index):
        def callback(future):
            if result.cancelled():
                return

            try:
                res = future.result()
            except _f.CancelledError:
                cancel_remaining()
                result.cancel()
            except Exception as err:
                cancel_remaining()
                result.set_exception(err)
            else:
                results_list[index] = res

            if all(x is not _undef for x in results_list):
                result.set_result(results_list)

        return callback

    result.set_running_or_notify_cancel()
    for index, future in enumerate(futures):
        future.add_done_callback(callback_for(index))

    return result


def chain(leader, *funcs):
    """ Chain futures together until all steps have been exhausted.

    - Final result can be either a deferred value or not, depends on the return
      type of the last step in chain.
    - Assumes futures are independantly submitted to an executor

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

    >>> f1 = _f.Future()
    >>> f3 = chain(f1, lambda x: deferred(x + 1), lambda x: x * 3)
    >>> f1.set_result(1)
    >>> f3.result()
    6
    """
    result = _f.Future()
    stack = list(funcs)[::-1]

    if callable(leader):
        stack.insert(0, leader)
        leader = deferred(None)

    def callback(future):
        try:
            res = future.result()
        except _f.CancelledError:
            result.cancel()
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
    leader.add_done_callback(callback)
    return result


def unwrap(future):
    """ Resolve nested futures until a non future is resolved or an
    exception is raised.

    :type future: concurrent.futures.Future
    :param future: Future to unwrap

    :rtype: any
    :returns: Unwrapped value

    >>> f1 = _f.Future()
    >>> f2 = _f.Future()
    >>> f3 = _f.Future()

    >>> nested = unwrap(f1)
    >>> f1.set_result(f2)
    >>> nested.running()
    True
    >>> f2.set_result(f3)
    >>> nested.running()
    True
    >>> f3.set_result(42)
    >>> nested.result()
    42
    """
    result = _f.Future()

    def callback(future):
        try:
            res = future.result()
        except _f.CancelledError:
            result.cancel()
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
    """

    def _step(original):
        return lambda _: original()  # Need to force a scope change

    return chain(deferred(None), *[_step(step) for step in steps])


def except_(future, exc_cls, func=lambda x: None):
    """ Except for futures.

    :type future: concurrent.futures.Future
    :param future: Future to wrap

    :type exc_cls: Union[type, Tuple[*type]]
    :param exc_cls: Exception classes to expect.
        Can be any value compatible with a standard ``except`` clause.

    :type func: Optional[callable]
    :param func:
        Will be passed the expected exception to generate the wrapped future's
        result.
        Default behaviour is to set the result to ``None``.

    >>> f1 = _f.Future()
    >>> f = except_(f1, ValueError, lambda err: err)
    >>> f1.set_exception(ValueError(1))

    >>> f.result()
    ValueError(1,)

    >>> f.exception() is None
    True
    """
    result = _f.Future()

    def callback(future):
        try:
            res = future.result()
        except _f.CancelledError:
            result.cancel()
        except exc_cls as err:
            result.set_result(func(err))
        except Exception as err:
            result.set_exception(err)
        else:
            result.set_result(res)

    result.set_running_or_notify_cancel()
    future.add_done_callback(callback)
    return result
