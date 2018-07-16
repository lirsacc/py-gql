# -*- coding: utf-8 -*-
""" Custom executor definitions.
"""
from concurrent import futures as _f

from ._concurrency import DummyFuture


class Executor(_f.Executor):
    future_factory = _f.Future


class SyncExecutor(Executor):
    """ Placeholder executor to work synchronously without leaving the
    current execution context. """

    future_factory = DummyFuture

    def submit(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def shutdown(self, wait=True):
        return True


DefaultExecutor = SyncExecutor


class ThreadPoolExecutor(Executor, _f.ThreadPoolExecutor):
    pass
