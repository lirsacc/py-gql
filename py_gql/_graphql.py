# -*- coding: utf-8 -*-
""" """

from inspect import isawaitable
from typing import (
    Any,
    Awaitable,
    Callable,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    cast,
)

from ._utils import MaybeAwaitable
from .exc import (
    ExecutionError,
    GraphQLResponseError,
    GraphQLSyntaxError,
    VariablesCoercionError,
)
from .execution import AsyncExecutor, Executor, GraphQLResult, SyncExecutor
from .lang import parse
from .schema import Schema
from .validation import ValidationVisitor, validate_ast


def _graphql(
    executor_cls: Type[Executor],
    schema: Schema,
    document: str,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
) -> MaybeAwaitable[GraphQLResult]:
    """ Main GraphQL entrypoint encapsulating query processing from start to
    finish.

    Args:
        executor: :class:`py_gql.execution.Executor` subclass to use.

        schema: Schema to execute the query against

        document: The query document

        variables: Raw, JSON decoded variables parsed from the request

        operation_name: Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value: Root resolution value passed to top-level resolver

        validators: Custom validators.
            Setting this will replace the defaults so if you just want to add
            some rules, append to :obj:`py_gql.validation.SPECIFIED_RULES`.

        context: Custom application-specific execution context.
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

        middlewares: List of middleware callable to use when resolving fields

    Returns:
        Execution result.
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

        result = executor_cls.execute_request(
            schema,
            ast,
            operation_name=operation_name,
            variables=variables,
            initial_value=root,
            context_value=context,
            middlewares=middlewares,
        )

        if isawaitable(result):

            async def deferred() -> GraphQLResult:
                try:
                    return await cast(Awaitable[GraphQLResult], result)
                except ExecutionError as err:
                    return GraphQLResult(data=None, errors=[err])

            return deferred()
        else:
            return result
    except GraphQLSyntaxError as err:
        return GraphQLResult(errors=[err])
    except VariablesCoercionError as err:
        return GraphQLResult(data=None, errors=err.errors)
    except ExecutionError as err:
        return GraphQLResult(data=None, errors=[err])


async def graphql(
    schema: Schema,
    document: str,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
) -> GraphQLResult:
    return await cast(
        Awaitable[GraphQLResult],
        _graphql(
            AsyncExecutor,
            schema,
            document,
            variables=variables,
            operation_name=operation_name,
            root=root,
            validators=validators,
            context=context,
            middlewares=middlewares,
        ),
    )


def graphql_sync(
    schema: Schema,
    document: str,
    variables: Optional[Mapping[str, Any]] = None,
    operation_name: Optional[str] = None,
    root: Any = None,
    context: Any = None,
    validators: Optional[Sequence[Type[ValidationVisitor]]] = None,
    middlewares: Optional[Sequence[Callable[..., Any]]] = None,
) -> GraphQLResult:
    return cast(
        GraphQLResult,
        _graphql(
            SyncExecutor,
            schema,
            document,
            variables=variables,
            operation_name=operation_name,
            root=root,
            validators=validators,
            context=context,
            middlewares=middlewares,
        ),
    )
