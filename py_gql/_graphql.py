# -*- coding: utf-8 -*-
""" Main GraphQL entrypoint encapsulating query processing from start to finish.
"""

from .exc import ExecutionError, GraphQLSyntaxError, VariablesCoercionError
from .execution import execute, GraphQLResult
from .execution._concurrency import is_deferred
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
        If specified, the operation with the given name will be executed. If not;
        this executes the single operation without disambiguation.

    :type initial_value: any
    :param initial_value: Root resolution value
        Will be passed to all top-level resolvers.

    :type context: any
    :param context:
        Custom application-specific execution context. Use this to pass in
        anything your resolvers require like database connection, user information, etc.
        Limits on the type(s) used here will depend on your own resolver
        implementations and the executor you use. MOst thread safe data-structures
        should work.

    :type middlewares: Optional[List[callable]]
    :param middlewares:
        List of middleware callable to consume when resolving fields.

    :type executor: py_gql.execution.executors.Executor
    :param executor: Custom executor to process resolver functions

    :rtype: GraphQLResult
    :returns: Execution result
    """

    assert isinstance(schema, Schema)
    schema.validate()

    try:
        ast = parse(document, allow_type_system=False)

        validators = SPECIFIED_RULES if validators is None else validators
        validation_result = validate_ast(schema, ast, validators=validators)

        if not validation_result:
            return GraphQLResult(errors=validation_result.errors)

    except GraphQLSyntaxError as err:
        return GraphQLResult(errors=[err])

    try:
        return execute(
            schema,
            ast,
            executor=executor,
            initial_value=initial_value,
            context_value=context,
            variables=variables,
            operation_name=operation_name,
            middlewares=middlewares,
        )
    except VariablesCoercionError as err:
        return GraphQLResult(data=None, errors=err.errors)
    except ExecutionError as err:
        return GraphQLResult(data=None, errors=[err])


def graphql(*args, **kwargs):
    timeout = kwargs.pop("timeout", None)
    result = _graphql(*args, **kwargs)
    if is_deferred(result):
        return result.result(timeout=timeout)
    return result
