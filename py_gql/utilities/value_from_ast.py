# -*- coding: utf-8 -*-
""" Utilities to extract Python values from an ast node. """

from ..exc import InvalidValue, UnknownVariable
from ..lang import ast as _ast
from ..schema import (
    EnumType,
    InputObjectType,
    ListType,
    NonNullType,
    ScalarType,
)


def value_from_ast(node, type_, variables=None):
    """ Convert an ast value node into a valid python value while validating
    against a given type.

    Warning:
        No validation is done with regard to the variable values which are
        assumed to have been validated before.

    Args:
        node (py_gql.lang.ast.Value): The value node
        variables (Optional[dict]): Variables mapping (coerced)
        type_ (py_gql.schema.Type): Type to validate against

    Returns:
        any: Extracted value

    Raises:
        :py:class:`TypeError`:
            when node is not a value node
        :class:`py_gql.exc.InvalidValue`:
            if the value cannot be converted
        :class:`py_gql.exc.UnknownVariable`:
            if a variable is required and doesn't exist
    """
    kind = type(node)

    if kind == _ast.Variable:
        varname = node.name.value
        if not variables or varname not in variables:
            raise UnknownVariable(varname, [node])
        variable_value = variables[varname]
        if isinstance(type_, NonNullType) and variable_value is None:
            raise InvalidValue(
                'Variable "$%s" used for type "%s" must not be null.'
                % (varname, type_),
                [node],
            )
        return variable_value

    if isinstance(type_, NonNullType):
        if kind == _ast.NullValue:
            raise InvalidValue("Expected non null value.", [node])
        else:
            type_ = type_.type

    if kind == _ast.NullValue:
        return None

    if isinstance(type_, ListType):
        if kind != _ast.ListValue:
            return [value_from_ast(node, type_.type, variables)]

        return [
            value_from_ast(item, type_.type, variables) for item in node.values
        ]

    if isinstance(type_, InputObjectType):
        if kind != _ast.ObjectValue:
            raise InvalidValue(
                "Expected Object but got %s" % kind.__name__, [node]
            )
        return _extract_input_object(node, type_, variables)

    if isinstance(type_, EnumType):
        if kind != _ast.EnumValue:
            raise InvalidValue("Expected EnumValue", [node])
        return type_.get_value(node.value)

    if isinstance(type_, ScalarType):
        return type_.parse_literal(node, variables)

    raise TypeError("Invalid type for input coercion %s" % type_)


def _extract_input_object(node, type_, variables):
    coerced = {}
    node_fields = {f.name.value: f for f in node.fields}
    for field in type_.fields:
        name = field.name
        if name not in node_fields:
            if field.has_default_value:
                coerced[name] = field.default_value
            elif isinstance(field.type, NonNullType):
                raise InvalidValue("Missing field %s" % name, [node])
        else:
            value = node_fields[name].value
            coerced[name] = value_from_ast(value, field.type, variables)

    return coerced
