# -*- coding: utf-8 -*-

from typing import Any, Callable, List, Mapping, Optional, Sequence, Type, cast

from .exc import (
    ExecutionError,
    GraphQLResponseError,
    GraphQLSyntaxError,
    VariablesCoercionError,
)
from .execution import AsyncExecutor, Executor, GraphQLResult, execute
from .execution.async_executor import unwrap_coro
from .lang import parse
from .schema import Schema
from .validation import ValidationVisitor, validate_ast


def do_graphql(
    # fmt: off
    schema: Schema,
    document: str,
    *,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    default_resolver: Optional[Callable[..., Any]] = None,
    executor_cls: Optional[Type[Executor]] = None,
    executor_args: Optional[Mapping[str, Any]] = None
    # fmt: on
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

        middlewares: List of middleware callable to use when resolving fields.

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
    schema.validate()

    try:
        ast = parse(document, allow_type_system=False)
        validation_result = validate_ast(schema, ast, validators=validators)

        if not validation_result:
            return GraphQLResult(
                errors=cast(
                    List[GraphQLResponseError], validation_result.errors
                )
            )

        return execute(
            schema,
            ast,
            operation_name=operation_name,
            variables=variables,
            initial_value=root,
            context_value=context,
            middlewares=middlewares,
            default_resolver=default_resolver,
            executor_cls=executor_cls,
            executor_args=executor_args,
        )
    except GraphQLSyntaxError as err:
        return GraphQLResult(errors=[err])
    except VariablesCoercionError as err:
        return GraphQLResult(data=None, errors=err.errors)
    except ExecutionError as err:
        return GraphQLResult(data=None, errors=[err])


async def graphql(
    # fmt: off
    schema: Schema,
    document: str,
    *,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    default_resolver: Optional[Callable[..., Any]] = None
    # fmt: on
) -> GraphQLResult:
    """
    Same as `handle_graphql_request` but enforcing usage of AsyncIO.

    Resolvers are expected to be async functions. Sync functions will be
    executed in a thread.
    """
    try:
        return cast(
            GraphQLResult,
            await unwrap_coro(
                do_graphql(
                    schema,
                    document,
                    variables=variables,
                    operation_name=operation_name,
                    root=root,
                    validators=validators,
                    context=context,
                    middlewares=middlewares,
                    default_resolver=default_resolver,
                    executor_cls=AsyncExecutor,
                )
            ),
        )
    except ExecutionError as err:
        return GraphQLResult(data=None, errors=[err])


def graphql_sync(
    # fmt: off
    schema: Schema,
    document: str,
    *,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
    default_resolver: Optional[Callable[..., Any]] = None
    # fmt: on
) -> GraphQLResult:
    """
    Same as `handle_graphql_request` but enforcing usage of sync resolvers.
    """
    return cast(
        GraphQLResult,
        do_graphql(
            schema,
            document,
            variables=variables,
            operation_name=operation_name,
            root=root,
            validators=validators,
            context=context,
            middlewares=middlewares,
            default_resolver=default_resolver,
        ),
    )
