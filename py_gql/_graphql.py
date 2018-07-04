# -*- coding: utf-8 -*-
""" Main GraphQL entrypoint encapsulating query processing from start to finish.
"""

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
    """ Full execution chain.

    :type schema: py_gql.schema.Schema
    :param schema: Schema to execute the query against

    :type document: str
    :param document: The query document.

    :type variables: dict
    :param variables: Raw, JSON decoded variables parsed from the request

    :type operation_name: Optional[str]
    :param operation_name: Operation to execute
        If specified, the operation with the given name will be executed. If
        not, this executes the single operation without disambiguation.

    :type initial_value: any
    :param initial_value: Root resolution value
        Will be passed to all top-level resolvers.

    :type validators: Optional[List[py_gql.validation.ValidationVisitor]]
    :param validators: Custom validators. Will replace the defaults.

    :type context: any
    :param context:
        Custom application-specific execution context. Use this to pass in
        anything your resolvers require like database connection, user
        information, etc.
        Limits on the type(s) used here will depend on your own resolver
        implementations and the executor you use. Most thread safe
        data-structures should work.

    :type middlewares: Optional[List[callable]]
    :param middlewares:
        List of middleware callable to consume when resolving fields.

    :type tracer: Optional[py_gql.execution.GraphQLTracer]
    :param tracer:
        Tracer instance.

    :type executor: py_gql.execution.executors.Executor
    :param executor: Custom executor to process resolver functions

    :rtype: Future[GraphQLResult]
    :returns: Deferred execution result
    """

    assert isinstance(schema, Schema)
    assert schema.validate()

    tracer = tracer or NullTracer()
    assert isinstance(tracer, GraphQLTracer)

    if not isinstance(tracer, NullTracer):
        middlewares = [tracer.middleware] + (middlewares or [])

    try:
        tracer.start()

        with tracer.trace_context("parse", document=document):
            ast = parse(document, allow_type_system=False)

        validators = SPECIFIED_RULES if validators is None else validators

        with tracer.trace_context("validate", ast=ast):
            validation_result = validate_ast(schema, ast, validators=validators)

        if not validation_result:
            tracer.end()
            return GraphQLResult(errors=validation_result.errors)
        else:
            tracer.trace("execute", "start", ast=ast, variables=variables)
            result = execute(
                schema,
                ast,
                executor=executor,
                initial_value=initial_value,
                context_value=context,
                variables=variables,
                operation_name=operation_name,
                middlewares=middlewares,
            )

            def close_trace(_):
                tracer.trace("execute", "end", ast=ast, variables=variables)
                tracer.end()

            result.add_done_callback(close_trace)
            return result

    except GraphQLSyntaxError as err:
        tracer.end()
        return GraphQLResult(errors=[err])
    except VariablesCoercionError as err:
        tracer.end()
        return GraphQLResult(data=None, errors=err.errors)
    except ExecutionError as err:
        tracer.end()
        return GraphQLResult(data=None, errors=[err])


def graphql(*args, **kwargs):
    """ Synchronous GraphQL entrypoint.

    :type schema: py_gql.schema.Schema
    :param schema: Schema to execute the query against

    :type document: str
    :param document: The query document.

    :type variables: dict
    :param variables: Raw, JSON decoded variables parsed from the request

    :type operation_name: Optional[str]
    :param operation_name: Operation to execute
        If specified, the operation with the given name will be executed. If
        not, this executes the single operation without disambiguation.

    :type initial_value: any
    :param initial_value: Root resolution value
        Will be passed to all top-level resolvers.

    :type validators: Optional[List[py_gql.validation.ValidationVisitor]]
    :param validators: Custom validators. Will replace the defaults.

    :type context: any
    :param context:
        Custom application-specific execution context. Use this to pass in
        anything your resolvers require like database connection, user
        information, etc.
        Limits on the type(s) used here will depend on your own resolver
        implementations and the executor you use. Most thread safe
        data-structures should work.

    :type middlewares: Optional[List[callable]]
    :param middlewares:
        List of middleware callable to consume when resolving fields.

    :type tracer: Optional[py_gql.execution.GraphQLTracer]
    :param tracer:
        Tracer instance.

    :type executor: py_gql.execution.executors.Executor
    :param executor: Custom executor to process resolver functions

    :type timeout: float
    :param timeout: Execution timeout in seconds.

    :rtype: GraphQLResult
    :returns: Execution result
    """
    timeout = kwargs.pop("timeout", None)
    result = _graphql(*args, **kwargs)
    if _concurrency.is_deferred(result):
        return result.result(timeout=timeout)
    return result
