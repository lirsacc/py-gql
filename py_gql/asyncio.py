# -*- coding: utf-8 -*-
""" AsyncIO support for python 3.5+.

.. warning::

    Importing this module outside of python 3.5+ will break.

"""

import asyncio
import functools as ft
import inspect
import logging

from .execution import _concurrency, executors
from ._graphql import _graphql


logger = logging.getLogger(__name__)


class AsyncIOExecutor(executors.Executor):
    """ Executor class adding support for async/await style coroutines.

    This expects the event loop to be managed externally and already running.

    .. warning::

        All non-coroutine functions submitted to this executor class will be
        run using `loop.run_in_executor` and potentially block execution for
        other coroutines.
    """

    Future = asyncio.futures.Future

    def __init__(self, event_loop=None):
        if event_loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = event_loop

        self._stopped = False
        self._id = 0
        self._futures = {}

    def submit(self, func, *args, **kwargs):
        if self._stopped:
            raise RuntimeError("Cannot schedule new futures after shutdown")

        if not self.loop.is_running():
            logger.warning(
                "Futures submitted to AsyncIOExecutor (%r) while the event "
                "loop (%r) is not running will not complete until the event "
                "loop is started.",
                self,
                self.loop,
            )

        self._id += 1
        id_ = self._id

        if inspect.iscoroutinefunction(func):
            coroutine = func(*args, **kwargs)
        else:
            coroutine = self.loop.run_in_executor(
                None, ft.partial(func, *args, **kwargs)
            )

        future = asyncio.ensure_future(coroutine, loop=self.loop)
        self._futures[id_] = future
        future.add_done_callback(lambda _: self._futures.pop(id_))
        return future

    def shutdown(self, wait=True):
        self._stopped = True
        if wait:
            remains = []
            for f in self._futures.values():
                if not f.done():
                    f.cancel()
                    remains.append(f)

    submit.__doc__ = executors.Executor.submit.__doc__
    shutdown.__doc__ = executors.Executor.shutdown.__doc__


async def graphql(*args, **kwargs):
    """
    """
    timeout = kwargs.pop("timeout", None)
    executor = kwargs.pop("executor", None)
    if executor is None:
        executor = AsyncIOExecutor()

    assert isinstance(executor, AsyncIOExecutor)

    result = _graphql(*args, **kwargs, executor=executor)
    if _concurrency.is_deferred(result):
        if not isinstance(result, asyncio.futures.Future):
            result = asyncio.wrap_future(result)
        return await asyncio.wait_for(
            result, timeout=timeout, loop=executor.loop
        )
    else:
        return result
