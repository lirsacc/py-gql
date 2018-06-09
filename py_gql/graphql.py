# -*- coding: utf-8 -*-
""" Main GraphQL entrypoint encapsulating query processing from start to finish.
"""

import json

from .exc import DocumentValidationError, GraphQLSyntaxError
from .execution import execute
from .lang import parse
from .validation import SPECIFIED_CHECKERS, validate_ast


def graphql(
    schema,
    document,
    variables,
    operation_name=None,
    initial_value=None,
    validators=None,
    validation_cache={},
    context=None,
    executor=None,
):
    """ Execute a graphql query against a schema.
    """

    try:
        ast = parse(document)
    except GraphQLSyntaxError as err:
        raise

    if validators or validators is None:
        if validation_cache and (schema, document) in validation_cache:
            validation_result = validation_cache[(schema, document)]
        else:
            validation_result = validate_ast(schema, ast, validators=validators)
            if validation_cache:
                validation_cache[(schema, document)] = validation_result

        if not validation_result:
            raise DocumentValidationError(validation_result.errors)

    try:
        result, execution_errors = execute(
            schema,
            ast,
            executor=executor,
            initial_value=initial_value,
            context=context,
            variables=variables,
        )
    except Exception as err:
        raise
