# -*- coding: utf-8 -*-

from typing import Any, Callable, Mapping, Optional, Sequence, Type, Union, cast

from .exc import (
    ExecutionError,
    GraphQLResponseError,
    GraphQLSyntaxError,
    VariablesCoercionError,
)
from .execution import (
    BlockingExecutor,
    Executor,
    GraphQLResult,
    Instrumentation,
    execute,
)
from .execution.runtime import AsyncIORuntime, Runtime
from .lang import parse
from .lang.ast import Document
from .schema import Schema
from .validation import ValidationVisitor, validate_ast


def process_graphql_query(
    schema: Schema,
    document: Union[str, Document],
    *,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    default_resolver: Optional[Callable[..., Any]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    instrumentation: Optional[Instrumentation] = None,
    disable_introspection: bool = False,
    executor_cls: Type[Executor] = Executor,
    runtime: Optional[Runtime] = None
) -> Any:
    """
    Main GraphQL entrypoint encapsulating query processing from start to
    finish including parsing, validation, variable coercion and execution.

    Args:
        schema: Schema to execute the query against

        document: The query document

        variables: Raw, JSON decoded variables parsed from the request

        operation_name: Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        root: Root resolution value passed to top-level resolver

        context: Custom application-specific execution context.
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

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
            keeping your API available. Note that this deviates the GraphQL
            specification and will likely break some clients so use this with
            caution.

        executor_cls: Executor class to use.
            **Must** be a subclass of `py_gql.execution.Executor`.

            This defines how your resolvers are going to be executed and the
            type of values you'll get out of this function. `executor_kwargs` will
            be passed on class instantiation as keyword arguments.

    Returns:
        Execution result.

    Warning:
        The returned value will depend on the executor class. They ususually
        return a type wrapping the `GraphQLResult` object such as
        `Awaitable[GraphQLResult]`. You can refer to `graphql_async` or
        `graphql_blocking` for example usage.
    """
    schema.validate()

    instrumentation = instrumentation or Instrumentation()
    runtime = runtime or Runtime()

    instrumentation.on_query_start()

    def _abort(*args, **kwargs):
        # Make sure the value is wrapped similarly to the execution result to
        # make it easier for consumers.
        return cast(Runtime, runtime).ensure_wrapped(
            _on_end(GraphQLResult(*args, **kwargs))
        )

    def _on_end(result: GraphQLResult) -> GraphQLResult:
        cast(Instrumentation, instrumentation).on_query_end()
        return cast(Instrumentation, instrumentation).transform_result(result)

    if isinstance(document, str):
        instrumentation.on_parsing_start()
        try:
            ast = parse(document)
        except GraphQLSyntaxError as err:
            return _abort(errors=[err])
        finally:
            instrumentation.on_parsing_end()
    else:
        ast = document

    try:
        ast = instrumentation.transform_ast(ast)
    except GraphQLResponseError as err:
        return _abort(errors=[err])

    instrumentation.on_validation_start()
    validation_result = validate_ast(schema, ast, validators=validators)
    instrumentation.on_validation_end()

    if not validation_result:
        return _abort(errors=validation_result.errors)

    try:
        return runtime.unwrap_value(
            runtime.map_value(
                execute(
                    schema,
                    ast,
                    operation_name=operation_name,
                    variables=variables,
                    initial_value=root,
                    context_value=context,
                    default_resolver=default_resolver,
                    instrumentation=instrumentation,
                    middlewares=middlewares,
                    disable_introspection=disable_introspection,
                    executor_cls=executor_cls,
                    runtime=runtime,
                ),
                _on_end,
            )
        )
    except VariablesCoercionError as err:
        return _abort(data=None, errors=err.errors)
    except ExecutionError as err:
        return _abort(data=None, errors=[err])


async def graphql(
    schema: Schema,
    document: Union[str, Document],
    *,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    default_resolver: Optional[Callable[..., Any]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    instrumentation: Optional[Instrumentation] = None
) -> GraphQLResult:
    """
    Same as `process_graphql_query` but enforcing usage of AsyncIO.

    Resolvers are expected to be async functions. Sync functions will be
    executed in a thread.
    """
    return cast(
        GraphQLResult,
        await process_graphql_query(
            schema,
            document,
            variables=variables,
            operation_name=operation_name,
            root=root,
            validators=validators,
            context=context,
            default_resolver=default_resolver,
            instrumentation=instrumentation,
            middlewares=middlewares,
            runtime=AsyncIORuntime(),
        ),
    )


def graphql_blocking(
    schema: Schema,
    document: Union[str, Document],
    *,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    default_resolver: Optional[Callable[..., Any]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    instrumentation: Optional[Instrumentation] = None
) -> GraphQLResult:
    """
    Same as `process_graphql_query` but enforcing usage of sync resolvers.
    """
    return cast(
        GraphQLResult,
        process_graphql_query(
            schema,
            document,
            variables=variables,
            operation_name=operation_name,
            root=root,
            validators=validators,
            context=context,
            default_resolver=default_resolver,
            instrumentation=instrumentation,
            middlewares=middlewares,
            executor_cls=BlockingExecutor,
        ),
    )
