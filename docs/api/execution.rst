Executing GraphQL queries
=========================

.. module: py_gql

.. automodule:: py_gql
    :members:
    :undoc-members:


Alternative executors
---------------------

.. automodule:: py_gql.execution.executors

.. autoclass:: py_gql.execution.executors.Executor
    :show-inheritance:

.. autoclass:: py_gql.execution.executors.SyncExecutor
    :show-inheritance:

.. autoclass:: py_gql.execution.executors.DefaultExecutor
    :show-inheritance:

.. autoclass:: py_gql.execution.executors.ThreadPoolExecutor
    :show-inheritance:

AsyncIO support
---------------

.. automodule:: py_gql.asyncio

.. autofunction:: py_gql.asyncio.graphql

.. autoclass:: py_gql.asyncio.AsyncIOExecutor
    :show-inheritance:
