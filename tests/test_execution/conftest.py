# -*- coding: utf-8 -*-
"""
"""

import pytest

from py_gql.execution import BlockingExecutor, Executor
from py_gql.execution.runtime import AsyncIORuntime, Runtime, ThreadPoolRuntime

from ._test_utils import assert_execution as assert_execution_original


@pytest.fixture(
    params=(
        pytest.param((Executor, Runtime), id="default"),
        pytest.param((BlockingExecutor, Runtime), id="blocking"),
        pytest.param((Executor, AsyncIORuntime), id="asyncio"),
        pytest.param((Executor, ThreadPoolRuntime), id="threadpool"),
    )
)
def assert_execution(request):

    executor_cls, runtime_cls = request.param

    async def _assert_execution(*args, **kwargs):
        return await assert_execution_original(
            *args, executor_cls=executor_cls, runtime=runtime_cls(), **kwargs
        )

    yield _assert_execution
