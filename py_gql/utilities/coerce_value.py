# -*- coding: utf-8 -*-
""" Utilities to validate Python values against a schema / types """

import json
from typing import Any, Dict, List, Mapping, Optional, Union

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
    Directive,
    EnumType,
    Field,
    GraphQLType,
    InputObjectType,
    ListType,
    NonNullType,
    ScalarType,
    Schema,
    is_input_type,
)
from .value_from_ast import value_from_ast

Path = List[Union[int, str]]


def _path(path):
    if not path:
        return []
    return ["value"] + path


def coerce_value(
    value: Any,
    type_: GraphQLType,
    node: Optional[_ast.Node] = None,
    path: Optional[Path] = None,
) -> Any:
    """ Coerce a Python value given a GraphQL Type.

    Args:
        value: Value to coerce
        type_: Expected type
        node: Relevant node
        path: Path into the value for nested values (lists, objects).
            Should only be set on recursive calls.

    Returns:
        The coerced value

    Raises:
        :class:`~py_gql.exc.CoercionError`: if coercion fails
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


def _coerce_list_value(
    value: Any, type_: ListType, node: Optional[_ast.Node], path: Path
) -> List[Any]:
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


def _coerce_input_object(
    value: Any, type_: InputObjectType, node: Optional[_ast.Node], path: Path
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CoercionError(
            "Expected type %s to be an object" % type_.name,
            node,
            value_path=_path(path),
        )

    coerced = {}
    errors = []

    for field in type_.fields:
        field_name = field.name

        if field_name not in value:
            if isinstance(field.type, NonNullType):
                errors.append(
                    CoercionError(
                        "Field %s of required type %s was not provided"
                        % (field_name, field.type),
                        node,
                        value_path=_path(path + [field_name]),
                    )
                )
        else:
            try:
                coerced[field.python_name] = coerce_value(
                    value[field_name], field.type, node, path + [field_name]
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


def coerce_argument_values(
    definition: Union[Field, Directive],
    node: Union[_ast.Field, _ast.Directive],
    variables: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Prepare a dict of argument values given a field or directive definition and
    a field or directive node.

    Args:
        definition:
            Field or Directive definition from which to extract argument definitions.

        node: Parse node

        variables: Coerced variable values

    Returns:
        Coerced arguments

    Raises:
        :class:`~py_gql.exc.CoercionError`:
            if any argument value fails to coerce, required argument is
            missing, etc.
    """
    variables = {} if variables is None else variables
    coerced_values = {}

    values = {a.name.value: a for a in node.arguments}
    for arg_def in definition.arguments:
        argname = arg_def.name
        target_name = arg_def.python_name
        argtype = arg_def.type
        if argname not in values:
            if arg_def.has_default_value:
                coerced_values[target_name] = arg_def.default_value
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
                    coerced_values[target_name] = variables[varname]
                elif arg_def.has_default_value:
                    coerced_values[target_name] = arg_def.default_value
                elif isinstance(argtype, NonNullType):
                    raise CoercionError(
                        'Argument "%s" of required type "%s" was provided the '
                        'missing variable "$%s"' % (argname, argtype, varname),
                        [node],
                    )
            else:
                try:
                    coerced_values[target_name] = value_from_ast(
                        arg.value, argtype, variables=variables
                    )
                except InvalidValue as err:
                    raise CoercionError(
                        'Argument "%s" of type "%s" was provided invalid value %s (%s)'
                        % (argname, argtype, print_ast(arg.value), err),
                        [node],
                    )

    return coerced_values


def directive_arguments(
    definition: Directive,
    node: _ast.SupportDirectives,
    variables: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Extract directive argument given a field or directive node and a directive
    definition.

    Args:
        definition: Directive definition from which to extract arguments

        node: Parse node

        variables: Coerced variable values

    Returns:
        Coerced directive arguments, ``None`` if the directive is not present
        on the node.

    Raises:
        :class:`~py_gql.exc.CoercionError`:
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


def coerce_variable_values(  # noqa: C901
    schema: Schema,
    operation: _ast.OperationDefinition,
    variables: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Prepare an object map of variable values of the correct type based on
    the provided operation definition and arbitrary JSON input. If the input
    cannot be parsed to match the variable definitions, an ExecutionError will
    be thrown. The returned value is a plain dict since it is exposed to user
    code.

    Extra variables are ignored and filtered out.

    Args:
        schema: GraphQL Schema to consider

        operation: Operation definition containing the variable definitions

        variables: Provided raw variables

    Returns:
        Coerced variables

    Raises:
        :class:`~py_gql.exc.VariablesCoercionError`:
            if any variable cannot be coerced.
    """
    coerced, errors = {}, []

    for var_def in operation.variable_definitions:
        name = var_def.variable.name.value

        try:
            var_type = schema.get_type_from_literal(var_def.type)
        except UnknownType:
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
                    'Variable "$%s" expected value of type "%s" which cannot be used '
                    "as an input type." % (name, print_ast(var_def.type)),
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
