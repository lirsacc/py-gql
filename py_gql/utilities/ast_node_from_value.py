# -*- coding: utf-8 -*-

import re
from typing import Any

from .._utils import is_iterable
from ..lang import ast as _ast
from ..schema import (
    ID,
    EnumType,
    Float,
    GraphQLType,
    InputObjectType,
    Int,
    ListType,
    NonNullType,
    ScalarType,
    is_input_type,
)
from ..schema.scalars import MAX_INT, MIN_INT, SPECIFIED_SCALAR_TYPES

_INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")


def ast_node_from_value(value: Any, input_type: GraphQLType) -> _ast.Value:
    """
    Infer an input value ast Node from a Python value given an input type.

    Args:
        value: Any python value that can be transformed into a node

        input_type: Input type used to disambiguate between node types.

    Return:
        Inferred value node

    Raises:
        :py:class:`ValueError`: when coercion into a node fails
    """
    if not is_input_type(input_type):
        raise TypeError('Expected input type but got "%r"' % input_type)

    if isinstance(input_type, NonNullType):
        node = ast_node_from_value(value, input_type.type)
        if isinstance(node, _ast.NullValue):
            raise ValueError('Value of type "%s" cannot be null' % input_type)
        return node

    if value is None:
        return _ast.NullValue()

    if isinstance(input_type, ListType):
        if is_iterable(value, strings=False):
            return _ast.ListValue(
                values=[
                    ast_node_from_value(entry, input_type.type)
                    for entry in value
                ]
            )
        return ast_node_from_value(value, input_type.type)

    if isinstance(input_type, InputObjectType):
        return _object_value_node_from_value(input_type, value)

    if isinstance(input_type, ScalarType):
        serialized = input_type.serialize(value)
    elif isinstance(input_type, EnumType):
        serialized = input_type.get_name(value)
    else:
        # Should never happen if previous precondition have been
        # implemented correctly.
        raise NotImplementedError()

    if serialized is None:
        return _ast.NullValue()

    try:
        return _scalar_node_from_value(input_type, serialized)
    except ValueError:
        pass

    raise ValueError(
        'Cannot convert value %r for type "%s"' % (value, input_type)
    )


def _object_value_node_from_value(
    input_type: InputObjectType, value: Any
) -> _ast.ObjectValue:
    if not isinstance(value, dict):
        raise ValueError('Value of type "%s" must be a dict' % input_type)

    field_nodes = []
    for field_def in input_type.fields:
        if field_def.name in value:
            field_value = ast_node_from_value(
                value[field_def.name], field_def.type
            )
            field_nodes.append(
                _ast.ObjectField(
                    name=_ast.Name(value=field_def.name), value=field_value
                )
            )
        elif field_def.required:
            raise ValueError(
                'Field "%s" of type "%s" is required'
                % (field_def.name, input_type)
            )

    return _ast.ObjectValue(fields=field_nodes)


def _scalar_node_from_value(
    input_type: GraphQLType, scalar_value: Any
) -> _ast.Value:
    if isinstance(scalar_value, bool):
        return _ast.BooleanValue(value=scalar_value)

    if isinstance(scalar_value, (int, float)):
        if input_type is Int:
            return _ast.IntValue(value=str(scalar_value))
        elif input_type is Float:
            int_value = int(scalar_value)
            if int_value == scalar_value and MIN_INT < int_value < MAX_INT:
                return _ast.IntValue(value=str(int_value))
        return _ast.FloatValue(value=str(scalar_value))

    if isinstance(scalar_value, str):
        if isinstance(input_type, EnumType):
            return _ast.EnumValue(value=scalar_value)
        elif input_type is ID and _INT_RE.match(scalar_value):
            return _ast.IntValue(value=scalar_value)
        elif (
            isinstance(input_type, ScalarType)
            and input_type not in SPECIFIED_SCALAR_TYPES
        ):
            if _INT_RE.match(scalar_value):
                int_value = int(scalar_value)
                if MIN_INT < int_value < MAX_INT:
                    return _ast.IntValue(value=scalar_value)
                else:
                    return _ast.FloatValue(value=scalar_value)
            try:
                fl = float(scalar_value)
            except ValueError:
                pass
            else:
                return _ast.FloatValue(value=str(fl))

        return _ast.StringValue(value=scalar_value)

    raise ValueError()
