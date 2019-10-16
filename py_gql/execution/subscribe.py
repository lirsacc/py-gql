# -*- coding: utf-8 -*-

import functools as ft
from typing import Any, Callable, Mapping, Optional, Type, cast

from ..exc import ExecutionError
from ..lang import ast as _ast
from ..schema import ObjectType, Schema
from ..utilities import coerce_variable_values
from .executor import Executor
from .get_operation import get_operation_with_type
from .instrumentation import Instrumentation
from .wrappers import GraphQLResult, ResolveInfo

Resolver = Callable[..., Any]


def subscribe(
    # fmt: off
    schema: Schema,
    document: _ast.Document,
    *,
    operation_name: Optional[str] = None,
    variables: Optional[Mapping[str, Any]] = None,
    initial_value: Optional[Any] = None,
    context_value: Optional[Any] = None,
    instrumentation: Optional[Instrumentation] = None,
    executor_cls: Type[Executor] = Executor,
    executor_kwargs: Optional[Mapping[str, Any]] = None
    # fmt: on
) -> Any:
    """
    Execute a GraphQL subscription against a schema and return the appropriate
    response stream. This assumes the query has been validated beforehand.

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

        tracer: Tracer instance.

        executor_cls: Executor class to use.
            **Must** be a subclass of `py_gql.execution.Executor`.

            This defines how your resolvers are going to be executed and the
            type of values you'll get out of this function. `executor_kwargs` will
            be passed on class instantiation as keyword arguments.

        executor_kwargs: Extra executor arguments.

    Returns:
        An iterator over subscription results.

    Warning:
        The returned value will depend on the executor class. They ususually
        return a type wrapping the `GraphQLResult` object such as
        `Awaitable[GraphQLResult]`. You can refer to `graphql_async` or
        `graphql_blocking` for example usage.
    """
    if not executor_cls.supports_subscriptions:
        raise RuntimeError(
            'Executor class "%r" doesn\'t support subscriptions.' % executor_cls
        )

    instrumentation = instrumentation or Instrumentation()

    operation, root_type = get_operation_with_type(
        schema, document, operation_name
    )
    coerced_variables = coerce_variable_values(
        schema, operation, variables or {}
    )

    if operation.operation != "subscription":
        raise RuntimeError(
            "`subscribe` does not support %s operation, "
            "use the `eecute` helper." % operation.operation
        )

    executor = executor_cls(
        schema,
        document,
        coerced_variables,
        context_value,
        instrumentation=instrumentation,
        # Enforce no middlewares for subscriptions.
        # TODO: This should work somehow but needs more work.
        middlewares=[],
        **(executor_kwargs or {}),
    )

    _on_event = ft.partial(
        execute_subscription_event, executor, root_type, operation
    )

    instrumentation.on_execution_start()

    # MapSourceToResponseEvent
    # Needs to be mapped to support async subscription resolvers.
    def _on_stream_created(source_stream):
        response_stream = executor.map_stream(source_stream, _on_event)

        cast(Instrumentation, instrumentation).on_execution_end()
        return response_stream

    return executor.ensure_wrapped(
        executor.map_value(
            create_source_event_stream(
                executor, root_type, operation, initial_value
            ),
            _on_stream_created,
        )
    )


def create_source_event_stream(
    executor: Executor,
    root_type: ObjectType,
    operation: _ast.OperationDefinition,
    initial_value: Optional[Any] = None,
) -> Any:
    fields = executor.collect_fields(
        root_type, operation.selection_set.selections
    )

    if len(fields) != 1:
        raise ExecutionError(
            "Subscription operation must specify only one field."
        )

    key, nodes = next(iter(fields.items()))
    node = nodes[0]

    field_def = executor.field_definition(root_type, node.name.value)

    if field_def is None:
        raise RuntimeError(
            "No field definition found for subscription field %s." % key
        )

    if field_def.subscription_resolver is None:
        raise RuntimeError(
            "Subscription field %s should provide a subscription resolver."
            % field_def.name
        )

    info = ResolveInfo(
        field_def,
        [key],
        root_type,
        executor.schema,
        executor.variables,
        executor.fragments,
        nodes,
    )

    coerced_args = executor.argument_values(field_def, node)

    return field_def.subscription_resolver(
        initial_value, executor.context_value, info, **coerced_args
    )


def execute_subscription_event(
    executor: Executor,
    root_type: ObjectType,
    operation: _ast.OperationDefinition,
    event: Any,
) -> Any:
    # As we carry the executor through the source stream iteration we need to
    # clear the errors between events.
    # REVIEW: We could split the Executor in 2 parts to maintain the benefit
    # of the caches while isolating the errors.
    executor.clear_errors()

    return executor.map_value(
        executor.unwrap_value(
            executor.execute_fields(
                root_type,
                event,
                [],
                executor.collect_fields(
                    root_type, operation.selection_set.selections
                ),
            )
        ),
        lambda data: GraphQLResult(data=data, errors=executor.errors),
    )
