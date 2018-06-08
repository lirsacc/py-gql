# -*- coding: utf-8 -*-
""" Custom executor definitions.
"""
from concurrent import futures as _f


class Executor(_f.Executor):
    """ Base graphql executor class """
    pass


class SyncExecutor(Executor):
    """ Placeholder executor to work synchronously without leaving the
    current execution context. """

    def submit(self, func, *args, **kwargs):
        future = _f.Future()

        try:
            result = func(*args, **kwargs)
            if callable(result):
                result = result()
        except Exception as e:
            future.set_exception(e)
        else:
            future.set_result(result)

        return future

    def shutdown(self, wait=True):
        return True


DefaultExecutor = SyncExecutor
