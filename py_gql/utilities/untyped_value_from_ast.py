# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional, Union

from ..exc import UnknownVariable
from ..lang import ast as _ast


def untyped_value_from_ast(
    node: Union[_ast.Value, _ast.Variable],
    variables: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Convert an ast value node into a valid python value without type validation.

    Warning:
        No validation is done with regard to the variable values which are
        assumed to have been validated before.

    Args:
        node: The value node
        variables: Variables mapping

    Returns:
        any: Extracted value

    Raises:

        :py:class:``TypeError``: when node is not a value node
        :class:`~py_gql.exc.UnknownVariable`:
            if a variable is required and doesn't exist
    """
    if isinstance(node, _ast.NullValue):
        return None
    elif isinstance(node, _ast.IntValue):
        return int(node.value, 10)
    elif isinstance(node, _ast.FloatValue):
        return float(node.value)
    elif isinstance(
        node, (_ast.StringValue, _ast.EnumValue, _ast.BooleanValue)
    ):
        return node.value
    elif isinstance(node, _ast.ListValue):
        return [
            untyped_value_from_ast(item, variables=variables)
            for item in node.values
        ]
    elif isinstance(node, _ast.ObjectValue):
        return {
            f.name.value: untyped_value_from_ast(f.value, variables=variables)
            for f in node.fields
        }
    elif isinstance(node, _ast.Variable):
        varname = node.name.value
        if not variables or varname not in variables:
            raise UnknownVariable(varname, [node])
        return variables[varname]

    raise TypeError("Unexpected node %s" % node.__class__)
