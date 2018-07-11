# -*- coding: utf-8 -*-
""" Custom executor definitions.
"""
from concurrent import futures as _f

Executor = _f.Executor


class SyncExecutor(Executor):
    """ Placeholder executor to work synchronously without leaving the
    current execution context. """

    def submit(self, func, *args, **kwargs):
        future = _f.Future()

        try:
            result = func(*args, **kwargs)
            if callable(result):
                result = result()
        except Exception as err:  # pylint: disable = broad-except
            future.set_exception(err)
        else:
            future.set_result(result)

        return future

    def shutdown(self, wait=True):
        return True


DefaultExecutor = SyncExecutor
ThreadPoolExecutor = _f.ThreadPoolExecutor
