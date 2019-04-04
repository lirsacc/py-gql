# -*- coding: utf-8 -*-

from typing import Any, Callable, Mapping, Optional, Sequence, Type, TypeVar

from ..exc import ExecutionError
from ..lang import ast as _ast
from ..schema import Schema
from ..utilities import coerce_variable_values
from .async_executor import AsyncExecutor  # noqa: F401
from .executor import Executor  # noqa: F401
from .threadpool_executor import ThreadPoolExecutor  # noqa: F401
from .wrappers import (  # noqa: F401
    GraphQLExtension,
    GraphQLResult,
    GroupedFields,
    ResolveInfo,
    ResponsePath,
)

__all__ = (
    "Executor",
    "AsyncExecutor",
    "GraphQLExtension",
    "GraphQLResult",
    "ResolveInfo",
    "ResponsePath",
    "ThreadPoolExecutor",
)

Resolver = Callable[..., Any]
TExecutorCls = TypeVar("TExecutorCls", bound=Type[Executor])


def execute(
    # fmt: off
    schema: Schema,
    document: _ast.Document,
    *,
    operation_name: Optional[str] = None,
    variables: Optional[Mapping[str, Any]] = None,
    initial_value: Optional[Any] = None,
    context_value: Optional[Any] = None,
    middlewares: Optional[Sequence[Resolver]] = None,
    executor_cls: Optional[TExecutorCls] = None,
    executor_args: Optional[Mapping[str, Any]] = None
    # fmt: on
) -> Any:
    operation = get_operation(document, operation_name)

    root_type = {
        "query": schema.query_type,
        "mutation": schema.mutation_type,
        "subscription": schema.subscription_type,
    }[operation.operation]

    if root_type is None:
        raise ExecutionError(
            "Schema doesn't support %s operation" % operation.operation
        )

    coerced_variables = coerce_variable_values(
        schema, operation, variables or {}
    )

    executor = (executor_cls or Executor)(
        schema,
        document,
        coerced_variables,
        context_value,
        middlewares or [],
        **(executor_args or {}),
    )

    if operation.operation == "query":
        exe_fn = executor.execute_fields
    elif operation.operation == "mutation":
        exe_fn = executor.execute_fields_serially
    else:
        # TODO: subscribtions.
        raise NotImplementedError("%s not supported" % operation.operation)

    fields = executor.collect_fields(
        root_type, operation.selection_set.selections
    )

    data = exe_fn(root_type, initial_value, [], fields)

    return executor.map_value(
        data, lambda d: GraphQLResult(data=d, errors=executor.errors)
    )


def get_operation(
    document: _ast.Document, operation_name: Optional[str] = None
) -> _ast.OperationDefinition:
    """ Extract relevant operation from a parsed document.

    In case the ``operation_name`` argument is null, the document is
    expected to contain only one operation which will be extracted.

    Args:
        document: Parsed document
        opeation_name: Operation to extract

    Returns: Relevant operation definition

    Raises:
        ExecutionError: No relevant operation can be found.
    """
    operations = [
        definition
        for definition in document.definitions
        if isinstance(definition, _ast.OperationDefinition)
    ]

    if not operations:
        raise ExecutionError("Expected at least one operation definition")

    if not operation_name:
        if len(operations) == 1:
            return operations[0]
        raise ExecutionError(
            "Operation name is required when document "
            "contains multiple operation definitions"
        )

    for operation in operations:
        if operation.name and operation.name.value == operation_name:
            return operation

    raise ExecutionError('No operation "%s" in document' % operation_name)
