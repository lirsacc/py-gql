# -*- coding: utf-8 -*-
""" Main GraphQL entrypoint encapsulating query processing from start to finish.
"""

import json

from ._utils import OrderedDict
from .exc import ExecutionError, GraphQLSyntaxError, VariablesCoercionError
from .execution import execute
from .lang import parse
from .schema import Schema
from .validation import SPECIFIED_RULES, validate_ast


def graphql(
    schema,
    document,
    variables=None,
    operation_name=None,
    initial_value=None,
    validators=None,
    context=None,
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
        result, execution_errors = execute(
            schema,
            ast,
            executor=executor,
            initial_value=initial_value,
            context_value=context,
            variables=variables,
            operation_name=operation_name,
        )
    except VariablesCoercionError as err:
        return GraphQLResult(data=None, errors=err.errors)
    except ExecutionError as err:
        return GraphQLResult(data=None, errors=[err])

    return GraphQLResult(data=result, errors=[err for err, _, _ in execution_errors])


_unset = object()


class GraphQLResult(object):
    """ Wrapper encoding the behaviour described in the Response part of the spec
    http://facebook.github.io/graphql/#sec-Response.
    """

    def __init__(self, data=_unset, errors=_unset):
        self._data = data
        self._errors = errors

    def __bool__(self):
        return not self._errors

    __nonzero__ = __bool__

    def response(self):
        d = OrderedDict()
        if self._errors is not _unset and self._errors:
            d["errors"] = [error.to_json() for error in self._errors]
        if self._data is not _unset:
            d["data"] = self._data
        return d

    def json(self, **kw):
        return json.dumps(self.response(), **kw)
