# -*- coding: utf-8 -*-
""" Middlewares provide support for modifying / short-circuiting each phase of
the execution of GraphQL a query:

    - Parsing
    - Validation
    - Field Resolution

"""

import functools as ft
import inspect

from . import _concurrency


class GraphQLMiddleware(object):
    """
    """

    def __call__(self, next_, root, args, context, info):
        return next_(root, args, context, info)


def _is_generator(callable_):
    if isinstance(callable_, GraphQLMiddleware):
        return inspect.isgeneratorfunction(callable_.__call__)
    return inspect.isgeneratorfunction(callable_)


def apply_middlewares(func, middlewares):
    """ Apply middleware functions to a base function.

    - Middlewares must the signature: ``(next, *args, **kwargs) -> any`` where
      ``(*args, **kwargs) -> any`` is the signature of the wrapped function.
    - They can either ``return`` or ``yield`` in order to have clean up logic
    - Generator based middlewares **must** yield at least once
    - Middlewares are evaluated inside-out

    >>> apply_middlewares(
    ...     lambda x: x * x,
    ...     [
    ...         lambda n, x: n(x + 1),
    ...         lambda n, x: n(x * 3)
    ...     ]
    ... )(1)
    36
    """
    if not middlewares:
        return func

    tail = func
    for mw in reversed(middlewares):
        assert callable(mw)
        if _is_generator(mw):
            mw = generator_middleware(mw)
        tail = ft.partial(mw, tail)

    tail = ft.wraps(func)(tail)
    return tail


def generator_middleware(func):
    """ Transform a middleware defined using the ``yield`` keyword into
    a usable middleware function.

    Middlewares defined as such are expected to ``yield`` only once and any
    non-yielding code present after the ``yield`` keyword is guaranteed to be
    run. """

    @ft.wraps(func)
    def wrapped(step, *args, **kwargs):
        gen = func(step, *args, **kwargs)

        def _finish(_):
            try:
                next(gen)
            except StopIteration:
                pass

        try:
            res = next(gen)
        except StopIteration:
            raise RuntimeError("Generator middleware did not yield")

        if _concurrency.is_deferred(res):
            res.add_done_callback(_finish)
        else:
            _finish(None)
        return res

    return wrapped
