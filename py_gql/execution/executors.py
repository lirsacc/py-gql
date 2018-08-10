# -*- coding: utf-8 -*-
""" Support for various runtime executors based on the :mod:`concurrent.futures`
API.

An executor is simply a subclass of :class:`concurrent.futures.Executor` which
is re-exported as :class:`~py_gql.execution.executors.Executor`.
"""
# TODO: Implement more executor options
from concurrent import futures as _f

from ._concurrency import DummyFuture

Executor = _f.Executor


class SyncExecutor(Executor):
    """ This is the default executor class which executes everything in a
    blocking manner. """

    # This tells the execution runtime which Future class to use when wrapping
    # values / consolidating multiple futures.
    # This one is much more lightweight then the standard Future and helps
    # alleviates the performance hit of using the executor / future abstractions
    # when everything is synchronous anyways.
    # REVIEW: This is awkward.
    Future = DummyFuture

    def submit(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def shutdown(self, wait=True):
        return True


DefaultExecutor = SyncExecutor
ThreadPoolExecutor = _f.ThreadPoolExecutor
