# -*- coding: utf-8 -*-

from typing import Any, Dict, Mapping, Optional, Union

from ..exc import InvalidValue, UnknownVariable
from ..lang import ast as _ast
from ..schema.types import (
    EnumType,
    GraphQLType,
    InputObjectType,
    ListType,
    NonNullType,
    ScalarType,
)


def value_from_ast(
    node: Union[_ast.Value, _ast.Variable],
    type_: GraphQLType,
    variables: Optional[Mapping[str, Any]] = None,
) -> Any:
    """
    Convert an ast value node into a valid python value while validating against
    a given type.

    Warning:
        No validation is done with regard to the variable values which are
        assumed to have been validated before.

    Args:
        node: The value node
        variables: Variables mapping (coerced)
        type_: Type to validate against

    Returns:
        Extracted value

    Raises:
        :py:class:`TypeError`:
            when node is not a value node

        :`~py_gql.exc.InvalidValue`:
            if the value cannot be converted

        :`~py_gql.exc.UnknownVariable`:
            if a variable is required and doesn't exist
    """
    if isinstance(node, _ast.Variable):
        return _extract_variable(node, type_, variables)

    if isinstance(type_, NonNullType):
        if isinstance(node, _ast.NullValue):
            raise InvalidValue("Expected non null value.", [node])
        else:
            type_ = type_.type

    if isinstance(node, _ast.NullValue):
        return None

    if isinstance(type_, ListType):
        if not isinstance(node, _ast.ListValue):
            return [value_from_ast(node, type_.type, variables)]

        return [
            value_from_ast(item, type_.type, variables) for item in node.values
        ]

    if isinstance(type_, InputObjectType):
        if not isinstance(node, _ast.ObjectValue):
            raise InvalidValue(
                "Expected Object but got %s" % node.__class__.__name__, [node]
            )
        return _extract_input_object(node, type_, variables)

    if isinstance(type_, EnumType):
        if not isinstance(node, _ast.EnumValue):
            raise InvalidValue("Expected EnumValue", [node])
        return type_.get_value(node.value)

    if isinstance(type_, ScalarType):
        if not isinstance(
            node,
            (
                _ast.IntValue,
                _ast.FloatValue,
                _ast.StringValue,
                _ast.BooleanValue,
            ),
        ):
            raise InvalidValue(
                "Invalid literal %s for scalar type %s"
                % (node.__class__.__name__, type_.name)
            )
        return type_.parse_literal(node, variables)

    raise TypeError("Invalid type for input coercion %s" % type_)


def _extract_input_object(
    node: _ast.ObjectValue,
    type_: InputObjectType,
    variables: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    coerced = {}
    node_fields = {f.name.value: f for f in node.fields}
    for field in type_.fields:
        name = field.name
        target_name = field.python_name
        if name not in node_fields:
            if field.has_default_value:
                coerced[target_name] = field.default_value
            elif isinstance(field.type, NonNullType):
                raise InvalidValue("Missing field %s" % name, [node])
        else:
            value = node_fields[name].value
            coerced[target_name] = value_from_ast(value, field.type, variables)

    return coerced


def _extract_variable(
    node: _ast.Variable,
    type_: GraphQLType,
    variables: Optional[Mapping[str, Any]],
) -> Any:
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
