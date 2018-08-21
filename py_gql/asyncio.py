# -*- coding: utf-8 -*-
""" Asynchronous execution support for use with Python 3.5+ and async/await
syntax.

Warning:
    Importing this module outside of python 3.5+ will break.
"""

import asyncio
import functools as ft
import inspect
import logging

from ._graphql import _graphql
from .execution.executors import Executor

logger = logging.getLogger(__name__)


class AsyncIOExecutor(Executor):
    """ Executor class adding support for async/await style coroutines.

    This expects the event loop to be managed externally and will not start it
    or schedule the submitted coroutines by itself.

    All non-coroutine functions submitted to this executor class will be run
    using `loop.run_in_executor` and potentially block execution for other
    coroutines.

    Args:
        loop (Optional[asyncio.BaseEventLoop]): Event loop to use,
            defaults to calling :func:`asyncio.get_event_loop()`.
    """

    Future = asyncio.futures.Future

    def __init__(self, loop=None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._stopped = False
        self._id = 0
        self._futures = {}

    def submit(self, func, *args, **kwargs):
        # REVIEW: Version of the executor that starts the event loop itself ?
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

    submit.__doc__ = Executor.submit.__doc__
    shutdown.__doc__ = Executor.shutdown.__doc__


async def graphql(*args, **kwargs):
    """ This is the main entrypoint for execution of GraphQL queries in an
    asyncio context.

    Args:
        schema (py_gql.schema.Schema): Schema to execute the query against

        document (str): The query document

        variables (Optional[dict]):
            Raw, JSON decoded variables parsed from the request

        operation_name (Optional[str]): Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value (Any): Root resolution value passed to all top-level
            resolvers

        validators (Optional[List[py_gql.validation.ValidationVisitor]]):
            Custom validators.
            Setting this will replace the defaults so if you just want to add
            some rules, append to :obj:`py_gql.validation.SPECIFIED_RULES`.

        context (Any): Custom application-specific execution context
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

        middlewares (Optional[List[Callable]]):
            List of middleware callable to use when resolving fields

        tracer (Optional[py_gql.GraphQLTracer]): Tracer instance

        executor (Optional[py_gql.execution.Executor]): Executor instance

        timeout (Union[float,int]): max. timeout in seconds

        loop (Optional[asyncio.BaseEventLoop]): Event loop to use,
            defaults to calling :func:`asyncio.get_event_loop()`.

    Returns:
        py_gql.GraphQLResult: Execution result
    """
    timeout = kwargs.pop("timeout", None)
    loop = kwargs.pop("loop", None) or asyncio.get_event_loop()
    executor = kwargs.pop("executor", None)
    if executor is None:
        executor = AsyncIOExecutor(loop=loop)

    result = _graphql(*args, **kwargs, executor=executor)
    return await asyncio.wait_for(
        asyncio.wrap_future(result), timeout=timeout, loop=loop
    )
