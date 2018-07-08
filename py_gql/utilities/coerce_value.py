# -*- coding: utf-8 -*-
""" Utilities to validate Python values against a schema / types """

import json

from .._utils import find_one
from ..exc import (
    CoercionError,
    InvalidValue,
    MultiCoercionError,
    ScalarParsingError,
    UnknownEnumValue,
    UnknownType,
    VariableCoercionError,
    VariablesCoercionError,
)
from ..lang import ast as _ast, print_ast
from ..schema import (
    EnumType,
    InputObjectType,
    ListType,
    NonNullType,
    ScalarType,
    is_input_type,
)
from .path import Path
from .value_from_ast import value_from_ast


def _path(path):
    if not path:
        return Path()
    return Path(["value"]) + path


def coerce_value(value, type_, node=None, path=None):
    """ Coerce a Python value given a GraphQL Type.

    Args:
        value (any): Value to coerce
        type_ (py_gql.schema.Type): Expected type
        node (Optional[py_gql.lang.ast.Node]): Relevant node
        path: (Optional[py_gql.utilities.Path]):
            Path into the value for nested values (lists, objects).
            Should only be set on recursive calls.

    Returns:
        any: The coerced value

    Raises:
        :class:`py_gql.exc.CoercionError` if coercion fails
    """
    if path is None:
        path = []

    if isinstance(type_, NonNullType):
        if value is None:
            raise CoercionError(
                "Expected non-nullable type %s not to be null" % type_,
                node,
                value_path=_path(path),
            )
        type_ = type_.type

    if value is None:
        return None

    if isinstance(type_, ScalarType):
        try:
            return type_.parse(value)
        except ScalarParsingError as err:
            raise CoercionError(str(err), node, value_path=_path(path))

    if isinstance(type_, EnumType):
        if isinstance(value, str):
            try:
                return type_.get_value(value)
            except UnknownEnumValue as err:
                raise CoercionError(str(err), node, value_path=_path(path))
        else:
            raise CoercionError(
                "Expected type %s" % type_, node, value_path=_path(path)
            )

    if isinstance(type_, ListType):
        return _coerce_list_value(value, type_, node, path)

    if isinstance(type_, InputObjectType):
        return _coerce_input_object(value, type_, node, path)


def _coerce_list_value(value, type_, node, path):
    if isinstance(value, (list, tuple)):
        coerced = []
        errors = []

        for index, entry in enumerate(value):
            try:
                coerced.append(
                    coerce_value(
                        entry, type_.type, node=node, path=path + [index]
                    )
                )
            except MultiCoercionError as err:
                for child_err in err.errors:
                    errors.append(child_err)
            except CoercionError as err:
                errors.append(err)

        if len(errors) > 1:
            raise MultiCoercionError(errors)
        elif len(errors) == 1:
            raise errors[0]

        return coerced
    else:
        return [coerce_value(value, type_.type, node=node, path=path + [0])]


def _coerce_input_object(value, type_, node, path):
    if not isinstance(value, dict):
        raise CoercionError(
            "Expected type %s to be an object" % type_,
            node,
            value_path=_path(path),
        )

    coerced = {}
    errors = []
    for field in type_.fields:
        if field.name not in value:
            if isinstance(field.type, NonNullType):
                errors.append(
                    CoercionError(
                        "Field %s of required type %s was not provided"
                        % (field.name, field.type),
                        node,
                        value_path=_path(path + [field.name]),
                    )
                )
        else:
            try:
                coerced[field.name] = coerce_value(
                    value[field.name], field.type, node, path + [field.name]
                )
            except MultiCoercionError as err:
                for child_err in err.errors:
                    errors.append(child_err)
            except CoercionError as err:
                errors.append(err)

    if len(errors) > 1:
        raise MultiCoercionError(errors)
    elif len(errors) == 1:
        raise errors[0]

    for fieldname in value.keys():
        if fieldname not in type_.field_map:
            raise CoercionError(
                "Field %s is not defined by type %s" % (fieldname, type_),
                node,
                value_path=_path(path),
            )

    return coerced


def coerce_argument_values(definition, node, variables=None):
    """ Prepare a dict of argument values given a field or directive
    definition and a field or directive node.

    Args:
        definition (Union[py_gql.schema.Directive, py_gql.schema.Field]):
            Field or Directive definition from which to extract argument
            definitions.
        node (Union[py_gql.lang.ast.Field, py_gql.lang.ast.Directive]):
            AST node
        variables (Optional[dict]):  Coerced variable values


    Returns:
        dict: Coerced arguments

    Raises:
        :class:`py_gql.exc.CoercionError`
            if any argument value fails to coerce, required argument is
            missing, etc.
    """
    variables = dict() if variables is None else variables
    coerced_values = {}

    values = {a.name.value: a for a in node.arguments}
    defs = definition.arguments
    for arg_def in defs:
        argname = arg_def.name
        argtype = arg_def.type
        if argname not in values:
            if arg_def.has_default_value:
                coerced_values[argname] = arg_def.default_value
            elif isinstance(argtype, NonNullType):
                raise CoercionError(
                    'Argument "%s" of required type "%s" was not provided'
                    % (argname, argtype),
                    [node],
                )
        else:
            arg = values[argname]
            if isinstance(arg.value, _ast.Variable):
                varname = arg.value.name.value
                if varname in variables:
                    coerced_values[argname] = variables[varname]
                elif arg_def.has_default_value:
                    coerced_values[argname] = arg_def.default_value
                elif isinstance(argtype, NonNullType):
                    raise CoercionError(
                        'Argument "%s" of required type "%s" was provided the '
                        'missing variable "$%s"' % (argname, argtype, varname),
                        [node],
                    )
            else:
                try:
                    coerced_values[argname] = value_from_ast(
                        arg.value, argtype, variables=variables
                    )
                except InvalidValue as err:
                    raise CoercionError(
                        'Argument "%s" of type "%s" was provided invalid value '
                        "%s (%s)"
                        % (argname, argtype, print_ast(arg.value), str(err)),
                        [node],
                    )

    return coerced_values


def directive_arguments(definition, node, variables=None):
    """ Extract directive argument given a field node and a directive
    definition.

    Args:
        definition (py_gql.schema.Directive):
            Directive definition from which to extract arguments
        node (py_gql.lang.ast.Field): Ast node
        variables (Optional[dict]): Coerced variable values

    Returns:
        Optional[dict]: Coerced directive arguments, ``None`` if the directive
        is not present on the node.

    Raises:
        :class:`py_gql.exc.CoercionError`
            if any directive argument value fails to coerce, required argument
            is missing, etc.
    """
    directive = find_one(
        node.directives, lambda d: d.name.value == definition.name
    )

    return (
        coerce_argument_values(definition, directive, variables)
        if directive is not None
        else None
    )


def coerce_variable_values(schema, operation, variables):  # noqa: C901
    """ Prepares an object map of variable values of the correct type based on
    the provided operation definition and arbitrary JSON input. If the input
    cannot be parsed to match the variable definitions, an ExecutionError will
    be thrown. The returned value is a plain dict since it is exposed to user
    code.

    Extra variables are ignored and filtered out.

    Args:
        schema (py_gql.schema.Schema): GraphQL Schema to consider
        operation (py_gql.lang.ast.OperationDefinition):
            Operation definition containing the variable definitions
        variables (dict): Provided raw variables

    Returns:
        dict: Coerced variables

    Raises:
        :class:`py_gql.exc.VariablesCoercionError`
            if any variable cannot be coerced.
    """
    coerced, errors = {}, []

    for var_def in operation.variable_definitions:
        name = var_def.variable.name.value

        try:
            var_type = schema.get_type_from_literal(var_def.type)
        except UnknownType as err:
            errors.append(
                VariableCoercionError(
                    'Unknown type "%s" for variable "$%s"'
                    % (print_ast(var_def.type), name),
                    [var_def],
                )
            )
            continue

        if not is_input_type(var_type):
            errors.append(
                VariableCoercionError(
                    'Variable "$%s" expected value of type "%s" which cannot '
                    "be used as an input type."
                    % (name, print_ast(var_def.type)),
                    [var_def],
                )
            )
            continue

        if name not in variables:
            if var_def.default_value is not None:
                try:
                    coerced[name] = value_from_ast(
                        var_def.default_value, var_type
                    )
                except InvalidValue as err:
                    errors.append(
                        VariableCoercionError(
                            'Variable "$%s" got invalid default value %s (%s)'
                            % (name, print_ast(var_def.default_value), err),
                            [var_def],
                        )
                    )
            elif isinstance(var_type, NonNullType):
                errors.append(
                    VariableCoercionError(
                        'Variable "$%s" of required type "%s" was not provided.'
                        % (name, var_type),
                        [var_def],
                    )
                )
        else:
            value = variables[name]
            if value is None and isinstance(var_type, NonNullType):
                errors.append(
                    VariableCoercionError(
                        'Variable "$%s" of required type "%s" must not be null.'
                        % (name, var_type),
                        [var_def],
                    )
                )
            else:
                try:
                    coerced[name] = coerce_value(value, var_type)
                except MultiCoercionError as err:
                    for child_err in err.errors:
                        errors.append(
                            VariableCoercionError(
                                'Variable "$%s" got invalid value %s (%s)'
                                % (
                                    name,
                                    json.dumps(value, sort_keys=True),
                                    child_err,
                                ),
                                [var_def],
                            )
                        )
                except (InvalidValue, CoercionError) as err:
                    errors.append(
                        VariableCoercionError(
                            'Variable "$%s" got invalid value %s (%s)'
                            % (name, json.dumps(value, sort_keys=True), err),
                            [var_def],
                        )
                    )

    if errors:
        raise VariablesCoercionError(errors)

    return coerced
