# -*- coding: utf-8 -*-
""" Custom executor definitions.
"""
from concurrent import futures as _f

Executor = _f.Executor


class SyncExecutor(Executor):
    """ Placeholder executor to work synchronously without leaving the
    current execution context. """

    def submit(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def shutdown(self, wait=True):
        return True


DefaultExecutor = SyncExecutor
ThreadPoolExecutor = _f.ThreadPoolExecutor
