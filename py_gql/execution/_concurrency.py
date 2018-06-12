# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module. """

from concurrent import futures as _f


def is_deferred(value):
    return isinstance(value, _f.Future)


def deferred(value):
    """ Transform a value into a ``Future`` awaitable object.

    :type value: any
    :param value: Original value

    :rtype: ``concurrent.futures.Future``
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

    :rtype: ``concurrent.futures.Future``
    :returns: Value wrapped in a ``Future`` if not alrady the case
    """
    if isinstance(maybe_future, _f.Future):
        return maybe_future
    return deferred(maybe_future)


def all_(futures):
    """ Create a Future from a list of futures that resolves only when all
    futures have resolved.

    :type futures: list[concurrent.futures.Future]
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


def chain(previous, *funcs):
    """ Chain futures together until all steps have been exhausted.

    - Final result can be either a deferred value or not, depends on the return
      type of the last step in chain.
    - Assumes futures are independantly submitted to an executor

    >>> f1 = _f.Future()
    >>> f3 = chain(f1, lambda x: deferred(x + 1), lambda x: x * 3)
    >>> f1.set_result(1)
    >>> f3.result()
    6
    """
    result = _f.Future()
    stack = list(funcs)[::-1]

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
    previous.add_done_callback(callback)
    return result


def unwrap(future):
    """ Resolve nested futures until a non future is resolved or an exception is raised.

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
    def _step(original):
        return lambda _: original()  # Need to force a scope chnage

    return chain(deferred(None), *[_step(step) for step in steps])


def except_(future, error_cls, func=lambda x: None):
    """ Except for futures.

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
        except error_cls as err:
            result.set_result(func(err))
        except Exception as err:
            result.set_exception(err)
        else:
            result.set_result(res)

    result.set_running_or_notify_cancel()
    future.add_done_callback(callback)
    return result