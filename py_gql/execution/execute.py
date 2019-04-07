# -*- coding: utf-8 -*-

from typing import Any, Callable, Mapping, Optional, Sequence, Type, TypeVar

from ..exc import ExecutionError
from ..lang import ast as _ast
from ..schema import Schema
from ..utilities import coerce_variable_values
from .executor import Executor
from .get_operation import get_operation
from .wrappers import GraphQLResult

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
