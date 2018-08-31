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
    class CollectFieldsMiddleware(object):
        def __init__(self):
            self.fields = []

        def __call__(self, next_, root, args, context, info):
            self.fields.append(info.path)
            return next_(root, args, context, info)

    collect_fields = CollectFieldsMiddleware()

"""

import functools as ft
from inspect import isgeneratorfunction

from . import _concurrency


def _is_generator(mw):
    return isgeneratorfunction(mw) or isgeneratorfunction(mw.__call__)


def apply_middlewares(func, middlewares):
    """ Apply middleware functions to a base function.

    - Middlewares must the signature: ``(next, *args, **kwargs) -> any`` where
      ``(*args, **kwargs) -> any`` is the signature of the wrapped function.
    - They can either ``return`` or ``yield`` in order to have clean up logic
    - Generator based middlewares **must** yield at least once
    - Middlewares are evaluated inside-out
    """
    if not middlewares:
        return func

    tail = func
    for mw in reversed(middlewares):
        assert callable(mw)
        if _is_generator(mw):
            mw = generator_middleware(mw)
        tail = ft.partial(mw, tail)

    return tail


def generator_middleware(func):
    """ Transform a middleware defined using the ``yield`` keyword into
    a usable middleware function.

    Middlewares defined as such are expected to ``yield`` only once and any
    non-yielding code present after the ``yield`` keyword is guaranteed to be
    run. """

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

        if _concurrency.is_future(res):
            res.add_done_callback(_finish)
        else:
            _finish(None)
        return res

    return wrapped
