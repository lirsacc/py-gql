# -*- coding: utf-8 -*-
from ..exc import UnknownVariable
from ..lang import ast as _ast


def untyped_value_from_ast(node, variables=None):
    """ Convert an ast value node into a valid python value without type
    validation.

    Args:
        node (py_gql.lang.ast.Value): The value node
        variables (Optional[dict]): Variables mapping (coerced)

    Returns:
        any: Extracted value

    Raises:

        :py:class:``TypeError``: when node is not a value node
        :class:`~py_gql.exc.UnknownVariable`:
            if a variable is required and doesn't exist
    """
    kind = type(node)

    if kind == _ast.NullValue:
        return None
    elif kind == _ast.IntValue:
        return int(node.value, 10)
    elif kind == _ast.FloatValue:
        return float(node.value)
    elif kind in (_ast.StringValue, _ast.EnumValue, _ast.BooleanValue):
        return node.value
    elif kind == _ast.ListValue:
        return [
            untyped_value_from_ast(item, variables=variables)
            for item in node.values
        ]
    elif kind == _ast.ObjectValue:
        return {
            f.name.value: untyped_value_from_ast(f.value, variables=variables)
            for f in node.fields
        }
    elif kind == _ast.Variable:
        varname = node.name.value
        if not variables or varname not in variables:
            raise UnknownVariable(varname, [node])
        return variables[varname]

    raise TypeError("Unexpected node %s" % node.__class__)
