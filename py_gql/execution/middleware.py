# -*- coding: utf-8 -*-
""" Middlewares provide support for modifying / short-circuiting the field
resolution part of the execution. A middleware is a callable that returns /
yields to the next step.

.. highlight:: python

    # Functional middleware
    def ensure_bar_middleware(next_, root, args, context, info):
        if args.get('foo') != 'bar':
            raise ResolverError('Not bar!')
        return next_(root, args, context, info)

    # Generator middleware
    def logging_middleware(next_, root, args, context, info):
        logger.debug('start', info.path)
        yield next_(root, args, context, info)
        logger.debug('end', info.path)

    # Class based middleware
    class CollectFieldsMiddleware:
        def __init__(self):
            self.fields = []

        def __call__(self, next_, root, args, context, info):
            self.fields.append(info.path)
            return next_(root, args, context, info)

    collect_fields = CollectFieldsMiddleware()

"""

# REVIEW: As middleware are run on each field, the generator versions can be
# expensive due to the number of check they make. We might be able to make
# stronger assumptions in order to optimise this.

import functools as ft
from inspect import isawaitable, iscoroutinefunction, isgeneratorfunction
from typing import Any, Callable, Sequence


def _check_func_or_callable(
    func: Callable[[Any], bool]
) -> Callable[[Any], bool]:
    @ft.wraps(func)
    def wrapped(value):
        return func(value) or func(value.__call__)

    return wrapped


_isgeneratorfunc = _check_func_or_callable(isgeneratorfunction)
_isasyncfunc = _check_func_or_callable(iscoroutinefunction)


def apply_middlewares(
    func: Callable[..., Any], middlewares: Sequence[Callable[..., Any]]
) -> Callable[..., Any]:
    """ Apply middleware functions to a base function.

    - Middlewares must have the signature: ``(next, *args, **kwargs) -> any``
        where ``(*args, **kwargs) -> any`` is the signature of the wrapped
        function.
    - They can either ``return`` or ``yield`` in order to have clean up logic
    - Generator based middlewares **must** yield at least once
    - Middlewares are evaluated inside-out
    """
    if not middlewares:
        return func

    tail = func
    for mw in reversed(middlewares):
        assert callable(mw)

        # Second part of this condition is for Pthon 3.5 where
        # `isgeneratorfunction` is true for async functions.
        if _isgeneratorfunc(mw) and not _isasyncfunc(mw):
            tail = wrap_with_generator_middleware(mw, tail)
        elif _isasyncfunc(tail) and not _isasyncfunc(mw):
            tail = wrap_async_with_sync(mw, tail)
        else:
            tail = ft.partial(mw, tail)

    return tail


def wrap_async_with_sync(mw, func):
    async def wrapped(*args, **kwargs):
        return await mw(func, *args, **kwargs)

    return wrapped


def wrap_with_generator_middleware(mw, func):
    def wrapped(*args, **kwargs):
        gen = mw(func, *args, **kwargs)

        def _run_cleanup():
            try:
                next(gen)
            except StopIteration:
                pass

        try:
            res = next(gen)
        except StopIteration:
            raise RuntimeError("Generator middleware did not yield")

        if isawaitable(res):

            async def _deferred():
                final = await res
                _run_cleanup()
                return final

            return _deferred()
        else:
            _run_cleanup()
        return res

    if _isasyncfunc(func):

        async def _wrapped(*args, **kwargs):
            return await wrapped(*args, **kwargs)

        return _wrapped

    return wrapped
