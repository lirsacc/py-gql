# -*- coding: utf-8 -*-

from typing import Any, Callable, Mapping, Optional, Type, TypeVar

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
    default_resolver: Optional[Resolver] = None,
    executor_cls: Optional[TExecutorCls] = None,
    executor_args: Optional[Mapping[str, Any]] = None
    # fmt: on
) -> Any:
    """
    Execute a GraphQL document against a schema.

    Args:
        schema: Schema to execute the query against

        document: The query document

        variables: Raw, JSON decoded variables parsed from the request

        operation_name: Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value: Root resolution value passed to top-level resolver

        context_value: Custom application-specific execution context.
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

        default_resolver: Alternative default resolver.
            For field which do not specify a resolver, this will be used instead
            of `py_gql.execution.default_resolver`.

        executor_cls: Executor class to use.
            **Must** be a subclass of `py_gql.execution.Executor`.

            This defines how your resolvers are going to be executed and the
            type of values you'll get out of this function. `executor_args` will
            be passed on class instantiation as keyword arguments.

        executor_args: Extra executor arguments.

    Returns:
        Execution result.

    Warning:
        The returned value will depend on the executor class. They ususually
        return a type wrapping the `GraphQLResult` object such as
        `Awaitable[GraphQLResult]`. You can refer to `graphql_async` or
        `graphql_sync` for example usage.
    """
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
        default_resolver=default_resolver,
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
