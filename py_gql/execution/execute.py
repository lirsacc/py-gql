# -*- coding: utf-8 -*-

from typing import Any, Callable, Mapping, Optional, Sequence, Type, cast

from ..lang import ast as _ast
from ..schema import Schema
from ..utilities import coerce_variable_values
from .executor import Executor
from .get_operation import get_operation_with_type
from .instrumentation import Instrumentation
from .runtime import BlockingRuntime, Runtime
from .wrappers import GraphQLResult

Resolver = Callable[..., Any]


def execute(
    schema: Schema,
    document: _ast.Document,
    *,
    operation_name: Optional[str] = None,
    variables: Optional[Mapping[str, Any]] = None,
    initial_value: Optional[Any] = None,
    context_value: Optional[Any] = None,
    default_resolver: Optional[Resolver] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    instrumentation: Optional[Instrumentation] = None,
    disable_introspection: bool = False,
    runtime: Optional[Runtime] = None,
    executor_cls: Type[Executor] = Executor
) -> Any:
    """
    Execute a GraphQL query or mutation against a schema. This assumes the query
    has been validated beforehand.

    Args:
        schema: Schema to execute the query against.

        document: The query document.

        variables: Raw, JSON decoded variables parsed from the request.

        operation_name: Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value: Root resolution value passed to the top-level resolver.

        context: Custom application-specific execution context.
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            and the runtime implementations used. Most thread safe data-structures
            should work with built in runtimes.

        validators: Custom validators.
            Setting this will replace the defaults so if you just want to add
            some rules, append to :obj:`py_gql.validation.SPECIFIED_RULES`.

        default_resolver: Alternative default resolver.
            For field which do not specify a resolver, this will be used instead
            of `py_gql.execution.default_resolver`.

        middlewares: List of middleware functions.
            Middlewares are used to wrap the resolution of **all** fields with
            common logic, they are good canidates for logging, authentication,
            and execution guards.

        instrumentation: Instrumentation instance.
            Use :class:`~py_gql.execution.MultiInstrumentation` to compose
            mutiple instances together.

        disable_introspection: Use this to prevent schema introspection.
            This can be useful when you want to hide your full schema while
            keeping your API available. Note that this deviates from the GraphQL
            specification and will likely break some clients (such as GraphiQL)
            so use this with caution.

        runtime: Runtime against which to execute field resolvers (defaults to
            `~py_gql.execution.runtime.BlockingRuntime()`).

        executor_cls: Executor class to use.
            The executor class defines the implementation of the GraphQL
            resolution algorithm. This **must** be a subclass of
            `py_gql.execution.Executor`.

    Returns:
        Execution result. Exact type dependant on the runtime.
    """
    instrumentation = instrumentation or Instrumentation()
    runtime = runtime or BlockingRuntime()

    operation, root_type = get_operation_with_type(
        schema, document, operation_name
    )
    coerced_variables = coerce_variable_values(
        schema, operation, variables or {}
    )

    executor = executor_cls(
        schema,
        document,
        coerced_variables,
        context_value,
        default_resolver=default_resolver,
        instrumentation=instrumentation,
        disable_introspection=disable_introspection,
        middlewares=middlewares,
        runtime=runtime,
    )

    if operation.operation == "query":
        exe_fn = executor.execute_fields
    elif operation.operation == "mutation":
        exe_fn = executor.execute_fields_serially
    elif operation.operation == "subscription":
        raise RuntimeError(
            "`execute` does not support subscriptions, "
            "use the `subscribe` helper."
        )
    else:
        raise AssertionError("Unknown operation type %s." % operation.operation)

    instrumentation.on_execution_start()

    def _on_finish(data):
        cast(Instrumentation, instrumentation).on_execution_end()
        return GraphQLResult(data=data, errors=executor.errors)

    return runtime.ensure_wrapped(
        runtime.map_value(
            runtime.unwrap_value(
                exe_fn(
                    root_type,
                    initial_value,
                    [],
                    executor.collect_fields(
                        root_type, operation.selection_set.selections
                    ),
                )
            ),
            _on_finish,
        )
    )
