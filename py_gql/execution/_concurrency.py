# -*- coding: utf-8 -*-
""" Helpers to work with futures and the concurrent module in a way similar
to promises """

from concurrent.futures import Future

_UNDEF = object()


def is_future(value, cache={}):  # pylint: disable = dangerous-default-value
    t = value.__class__
    if t not in cache:
        cache[t] = callable(getattr(t, "add_done_callback", None))
    return cache[t]


def gather(futures):
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

    Returns:
        concurrent.futures.Future: Wrapped future
    """

    if not futures:
        return defer([])

    result = Future()
    results_list = [_UNDEF] * len(futures)
    # Using a list bypasses the global / nonlocal issue.
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
        if is_future(future):
            future.add_done_callback(callback_for(index))
        else:
            results_list[index] = future
            done_count[0] += 1

    notify()
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

    Returns:
        concurrent.futures.Future: Wrapped future
    """
    stack = iter(funcs)

    def _next(value):
        if is_future(value):
            return unwrap(_chain_one(value, _next))
        try:
            func = next(stack)
        except StopIteration:
            if is_future(value):
                return value
            return defer(value)
        else:
            return _next(func(value))

    return _next(leader)


def unwrap(source_future):
    """ Resolve nested futures until a non future is resolved or an
    exception is raised.

    Args:
        source_future (concurrent.futures.Future): Future to wrap

    Returns:
        concurrent.futures.Future: Wrapped future
    """
    result = Future()

    def callback(future):
        try:
            res = future.result()
        except Exception as err:  # pylint: disable = broad-except
            result.set_exception(err)
        else:
            if is_future(res):
                res.add_done_callback(callback)
            else:
                result.set_result(res)

    source_future.add_done_callback(callback)
    return result


def serial(steps):
    """ Similar to :func:`chain` but ignoring the intermediate results.

    Each step is called only after the result of the previous step has
    resolved. The resulting future rejects on the first step that rejects.

    Args:
        steps (Iterable[() -> concurrent.futures.Future]):

    Returns:
        concurrent.futures.Future: Wrapped future
    """

    def _step(original):
        return lambda _: original()

    return chain(None, *[_step(step) for step in steps])


def catch_exception(
    source_future, exc_cls=(Exception,), map_exception=lambda x: None
):
    """ Except for futures.

    Args:
        source_future (concurrent.futures.Future): Future to wrap
        exc_cls: Exception to catch, same type as when using ``except``
        map_ (Callable): Called on the caught exception to generate the final
            result. Default behaviour is to set the result to ``None``.

    Returns:
        concurrent.futures.Future: Wrapped future
    """
    result = Future()

    def callback(future):
        try:
            res = future.result()
        except exc_cls as err:
            result.set_result(map_exception(err))
        except Exception as err:  # pylint: disable = broad-except
            result.set_exception(err)
        else:
            result.set_result(res)

    source_future.add_done_callback(callback)
    return result


def defer(result=None, exc=None):
    """ Create a future instance with a known result. """
    f = Future()
    if exc:
        f.set_exception(exc)
    f.set_result(result)
    return f
