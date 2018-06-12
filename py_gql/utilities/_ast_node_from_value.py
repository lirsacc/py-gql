# -*- coding: utf-8 -*-

import re
import six

from ..lang import ast as _ast
from ..schema import (
    ID,
    EnumType,
    Float,
    InputObjectType,
    Int,
    ListType,
    NonNullType,
    ScalarType,
    is_input_type,
)
from ..schema.scalars import DefaultCustomScalar

_INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")


def ast_node_from_value(value, input_type):  # noqa
    """ Infer an ast Node for a Python value given a given input type.

    :type value: any
    :param value:

    :type input_type: py_gql.schema.Type
    :param input_type:

    :rtype: py_gql.lang.ast.Node
    :returns:
    """
    assert is_input_type(input_type)
    if isinstance(input_type, NonNullType):
        node = ast_node_from_value(value, input_type.type)
        if isinstance(node, _ast.NullValue):
            raise ValueError('Value of type "%s" cannot be null' % input_type)
        return node

    if value is None:
        return _ast.NullValue()

    if isinstance(input_type, ListType):
        if isinstance(value, (list, tuple)):
            return _ast.ListValue(
                value=[ast_node_from_value(entry, input_type.type) for entry in value]
            )
        return ast_node_from_value(value, input_type.type)

    if isinstance(input_type, InputObjectType):
        if not isinstance(value, dict):
            raise ValueError('Value of type "%s" must be a dict')

        field_nodes = []
        for field_def in input_type.fields:
            if field_def.name in value:
                field_value = ast_node_from_value(value[field_def.name], field_def.type)
                field_nodes.append(
                    _ast.ObjectField(
                        name=_ast.Name(value=field_def.name), value=field_value
                    )
                )
            elif field_def.required:
                raise ValueError(
                    'Field "%s" of type "%s" is required' % (field_def.name, input_type)
                )

        return _ast.ObjectValue(fields=field_nodes)

    if isinstance(input_type, ScalarType):
        serialized = input_type.serialize(value)

    if isinstance(input_type, EnumType):
        serialized = input_type.get_name(value)

    if serialized is None:
        return _ast.NullValue()

    if isinstance(serialized, bool):
        return _ast.BooleanValue(value=serialized)

    if isinstance(serialized, (int, float)):
        if input_type is Int:
            return _ast.IntValue(value=str(serialized))
        elif input_type is Float:
            if int(serialized) == serialized and -2147483647 < serialized < 2147483647:
                return _ast.IntValue(value=str(int(serialized)))
            elif -2147483647 < serialized < 2147483647:
                return _ast.FloatValue(value=str(serialized))
            return _ast.FloatValue(value="%.g" % serialized)

    if isinstance(serialized, six.string_types):
        if isinstance(input_type, EnumType):
            return _ast.EnumValue(value=serialized)
        elif input_type is ID and _INT_RE.match(serialized):
            return _ast.IntValue(value=serialized)
        elif isinstance(input_type, DefaultCustomScalar):
            if _INT_RE.match(serialized):
                intvalue = int(serialized)
                if -2147483647 < intvalue < 2147483647:
                    return _ast.IntValue(value=serialized)
                else:
                    return _ast.FloatValue(value=serialized)
            try:
                float(serialized)
            except ValueError:
                pass
            else:
                return _ast.FloatValue(value="%.g" % serialized)

        return _ast.StringValue(value=serialized)

    raise ValueError('Cannot convert value %r of type "%s"' % (value, input_type))
