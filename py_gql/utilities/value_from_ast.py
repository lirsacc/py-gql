# -*- coding: utf-8 -*-
""" Utilities to extract Python values from an ast node.

In large part ported from the JS implementation and adapted to
work with the schema / types implementation we have.
"""

from ..exc import InvalidValue, UnknownVariable
from ..lang import ast as _ast
from ..schema.types import EnumType, InputObjectType, ListType, NonNullType, ScalarType


def untyped_value_from_ast(node, variables=None):
    """ Convert an ast value node into a valid python value
    without type validation.

    :type node: py_gql.lang.ast.Value
    :param node:
        The value node which value is required

    :type variables: dict[str, any]|None
    :param variables:
        Variables mapping.

    :rtype: any
    :returns:
        Extracted value.
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
            untyped_value_from_ast(item, variables=variables) for item in node.values
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


def typed_value_from_ast(node, type_, variables=None):
    """ Convert an ast value node into a valid python value
    while vaidating against a given type.
    Raise ``py_gql.exc.InvalidValue`` when conversion fails.

    :type node: py_gql.lang.ast.Value
    :param node:
        The value node which value is required.

    :type type_: py_gql.schema.types.Type
    :param type_:
        Type to validate against.

    :type variables: dict[str, any]|None
    :param variables:
        Variables mapping.

    :rtype: any
    :returns:
        Coerced value.
    """

    # [WARN] This is slightly different from the JS reference:
    # - It raises on missing variables instead of nullifying
    # - It doesn't wrap singletons scalars in list types

    kind = type(node)
    if isinstance(type_, NonNullType):
        if kind == _ast.NullValue:
            raise InvalidValue("Expected non null value.", [node])
        else:
            type_ = type_.type

    if kind == _ast.NullValue:
        return None

    if kind == _ast.Variable:
        varname = node.name.value
        if not variables or varname not in variables:
            raise UnknownVariable(varname, [node])
        # [WARN] No validation of the variable value is done here as
        # we expect the query to have been validated and the variable usage
        # to be of the correct type.
        return variables[varname]

    if isinstance(type_, ListType):
        if kind != _ast.ListValue:
            return [typed_value_from_ast(node, type_.type, variables)]

        # [WARN] The ref implementation nullifies nullable missing entries
        # => check spec for this behaviour.
        return [
            typed_value_from_ast(item, type_.type, variables) for item in node.values
        ]

    if isinstance(type_, InputObjectType):
        if kind != _ast.ObjectValue:
            raise InvalidValue("Expected Object but got %s" % kind.__name__, [node])
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
            # [WARN] As-is missing field will remain missing in the
            # resulting object, not sure if that's what the spec says.
        else:
            value = node_fields[name].value
            coerced[name] = typed_value_from_ast(value, field.type, variables)

    return coerced
