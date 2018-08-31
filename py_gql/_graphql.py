# -*- coding: utf-8 -*-
""" """

import functools as ft

from .exc import ExecutionError, GraphQLSyntaxError, VariablesCoercionError
from .execution import GraphQLResult, GraphQLTracer, _concurrency, execute
from .execution.tracing import NullTracer
from .lang import parse
from .schema import Schema
from .validation import SPECIFIED_RULES, validate_ast


def _graphql(
    schema,
    document,
    variables=None,
    operation_name=None,
    initial_value=None,
    validators=None,
    context=None,
    middlewares=None,
    tracer=None,
    executor=None,
):
    """ Main GraphQL entrypoint encapsulating query processing from start to
    finish.

    Args:
        schema (py_gql.schema.Schema): Schema to execute the query against

        document (str): The query document

        variables (Optional[dict]):
            Raw, JSON decoded variables parsed from the request

        operation_name (Optional[str]): Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value (Any): Root resolution value passed to all top-level
            resolvers

        validators (Optional[List[py_gql.validation.ValidationVisitor]]):
            Custom validators.
            Setting this will replace the defaults so if you just want to add
            some rules, append to :obj:`py_gql.validation.SPECIFIED_RULES`.

        context (Any): Custom application-specific execution context
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

        middlewares (Optional[List[Callable]]):
            List of middleware callable to use when resolving fields

        tracer (Optional[py_gql.GraphQLTracer]): Tracer instance

        executor (Optional[py_gql.execution.Executor]): Executor instance

    Returns:
        Future: Deferred execution result
    """

    assert isinstance(schema, Schema)
    schema.validate()

    tracer = tracer or NullTracer()
    assert isinstance(tracer, GraphQLTracer)

    if not isinstance(tracer, NullTracer):
        middlewares = [tracer._middleware] + (middlewares or [])

    try:
        tracer.trace(
            "query",
            "start",
            document=document,
            variables=variables,
            operation_name=operation_name,
        )

        _close_trace = ft.partial(
            tracer.trace,
            "query",
            "end",
            document=document,
            variables=variables,
            operation_name=operation_name,
        )

        with tracer._trace_context("parse", document=document):
            ast = parse(document, allow_type_system=False)

        validators = SPECIFIED_RULES if validators is None else validators

        with tracer._trace_context("validate", ast=ast):
            validation_result = validate_ast(schema, ast, validators=validators)

        if not validation_result:
            _close_trace()
            return _concurrency.defer(
                GraphQLResult(errors=validation_result.errors)
            )
        else:
            tracer.trace("execute", "start", ast=ast, variables=variables)

            def _close(res):
                tracer.trace("execute", "end", ast=ast, variables=variables)
                _close_trace()
                return res

            return _concurrency.chain(
                execute(
                    schema,
                    ast,
                    executor=executor,
                    initial_value=initial_value,
                    context_value=context,
                    variables=variables,
                    operation_name=operation_name,
                    middlewares=middlewares,
                ),
                _close,
            )

    except GraphQLSyntaxError as err:
        _close_trace()
        return _concurrency.defer(GraphQLResult(errors=[err]))
    except VariablesCoercionError as err:
        _close_trace()
        return _concurrency.defer(GraphQLResult(data=None, errors=err.errors))
    except ExecutionError as err:
        _close_trace()
        return _concurrency.defer(GraphQLResult(data=None, errors=[err]))


def graphql(
    schema,
    document,
    variables=None,
    operation_name=None,
    initial_value=None,
    validators=None,
    context=None,
    middlewares=None,
    tracer=None,
    executor=None,
    timeout=None,
):
    """ This is the main entrypoint for execution of GraphQL queries.

    Args:
        schema (py_gql.schema.Schema): Schema to execute the query against

        document (str): The query document

        variables (Optional[dict]):
            Raw, JSON decoded variables parsed from the request

        operation_name (Optional[str]): Operation to execute
            If specified, the operation with the given name will be executed.
            If not, this executes the single operation without disambiguation.

        initial_value (Any): Root resolution value passed to all top-level
            resolvers

        validators (Optional[List[py_gql.validation.ValidationVisitor]]):
            Custom validators.
            Setting this will replace the defaults so if you just want to add
            some rules, append to :obj:`py_gql.validation.SPECIFIED_RULES`.

        context (Any): Custom application-specific execution context
            Use this to pass in anything your resolvers require like database
            connection, user information, etc.
            Limits on the type(s) used here will depend on your own resolver
            implementations and the executor class you use. Most thread safe
            data-structures should work.

        middlewares (Optional[List[Callable]]):
            List of middleware callable to use when resolving fields

        tracer (Optional[py_gql.GraphQLTracer]): Tracer instance

        executor (Optional[py_gql.execution.Executor]): Executor instance

        timeout (Union[float,int]): blocking timeout in seconds
            When using custom executors which support non-blocking / parallel
            execution, the call will block until the execution result is
            available or ``timeout`` is exceeded, however by default timeout
            has no effect as the resolution is blocking.

    Returns:
        py_gql.GraphQLResult: Execution result
    """
    return _graphql(
        schema,
        document,
        variables=variables,
        operation_name=operation_name,
        initial_value=initial_value,
        validators=validators,
        context=context,
        middlewares=middlewares,
        tracer=tracer,
        executor=executor,
    ).result(timeout=timeout)
