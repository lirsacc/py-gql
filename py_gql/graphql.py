# -*- coding: utf-8 -*-
""" This is the main entrypoint for parsing a query and
validating + executing it against a given schema.
"""

# from .lang import parse
# from .validation import validate
# from .execution import execute


# def graphql(schema, query='', ctx=None, root_value=None,
#             variable_values=None, operation_name=None):
#     """ This is the main entrypoint for parsing a query and
#     validating + executing it against a given schema.

#     :type schema: py_gql.schema.Schema
#     :param schema:
#         The root GraphQL schema

#     :type query: str|py_gql.lang.Source
#     :param query:
#         The GraphQL document

#     :type ctx: dict
#     :param ctx:
#         Execution context to forward to resolver functions

#     :rtype: dict
#     :returns:
#         The resolved result for the query
#     """
#     ast = parse(query)
#     validate(schema, ast)
#     return execute(schema, ast, ctx=ctx)
