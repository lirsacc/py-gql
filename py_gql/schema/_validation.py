# -*- coding: utf-8 -*-
""" Schema validation utility """

import re

from ..exc import SchemaError
from .introspection import is_introspection_type
from .scalars import SPECIFIED_SCALAR_TYPES
from .types import (
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    InputField,
    InputObjectType,
    InterfaceType,
    NonNullType,
    ObjectType,
    UnionType,
    is_input_type,
    is_output_type,
)

VALID_NAME_RE = re.compile(r"^[_a-zA-Z][_a-zA-Z0-9]*$")
RESERVED_NAMES = set((t.name for t in SPECIFIED_SCALAR_TYPES))


def validate_schema(schema):
    """ Validate a provided GraphQL schema.

    Useful for handling untrusted schemas or during development, but ideally
    you do not need to run this in production when controlling the schema.

    Args:
        schema (py_gql.schema.Schema):

    Returns:
        bool: Whether or not the schema is valid

    Raises:
        :class:`~py_gql.exc.SchemaError` if the schema is invalid.
    """
    for type_ in schema.types.values():
        _assert(
            type_ and hasattr(type_, "name"),
            "Expected named type but got %s" % type_,
        )
        _assert(
            is_introspection_type(type_)
            or type_ in SPECIFIED_SCALAR_TYPES
            or _is_valid_name(type_.name),
            'Invalid type name "%s", '
            "must match /^[_a-zA-Z][_a-zA-Z0-9]*$/" % type_.name,
        )

    validate_root_types(schema)
    validate_directives(schema)

    for type_ in schema.types.values():
        if isinstance(type_, ObjectType):
            validate_fields(schema, type_)
            validate_interfaces(schema, type_)
        elif isinstance(type_, InterfaceType):
            validate_fields(schema, type_)
        elif isinstance(type_, UnionType):
            validate_union_members(schema, type_)
        elif isinstance(type_, EnumType):
            validate_enum_values(schema, type_)
        elif isinstance(type_, InputObjectType):
            validate_input_fields(schema, type_)

    return True


def _assert(predicate, msg):
    """
    >>> _assert(True, 'foo')
    >>> _assert(False, 'foo')
    Traceback (most recent call last):
        ...
    py_gql.exc.SchemaError: foo
    """
    if not predicate:
        raise SchemaError(msg)


def _is_valid_name(name):
    """
    >>> _is_valid_name('foo_bar')
    True

    >>> _is_valid_name('fooBar')
    True

    >>> _is_valid_name('FooBar')
    True

    >>> _is_valid_name('_foo_bar')
    True

    >>> _is_valid_name('foo-bar')
    False

    >>> _is_valid_name('__foo_bar')
    False

    >>> _is_valid_name('')
    False

    >>> _is_valid_name('42')
    False
    """
    return bool(
        name and not name.startswith("__") and VALID_NAME_RE.match(name)
    )


def _assert_valid_name(name):
    _assert(
        _is_valid_name(name),
        'Invalid name "%s", must match /^[_a-zA-Z][_a-zA-Z0-9]*$/' % name,
    )


def validate_root_types(schema):
    """
    Args:
        schema (py_gql.schema.Schema):
    """
    _assert(schema.query_type is not None, "Must provide Query type")
    if schema.query_type is not None:
        _assert(
            isinstance(schema.query_type, ObjectType),
            'Query must be ObjectType but got "%s"' % schema.query_type,
        )
        _assert_valid_name(schema.query_type.name)

    if schema.mutation_type is not None:
        _assert(
            isinstance(schema.mutation_type, ObjectType),
            'Mutation must be ObjectType but got "%s"' % schema.mutation_type,
        )
        _assert_valid_name(schema.mutation_type.name)

    if schema.subscription_type is not None:
        _assert(
            isinstance(schema.subscription_type, ObjectType),
            'Subscription must be ObjectType but got "%s"'
            % schema.subscription_type,
        )
        _assert_valid_name(schema.subscription_type.name)


def validate_directives(schema):
    """
    Args:
        schema (py_gql.schema.Schema):
    """
    for directive in schema.directives.values():
        _assert(
            isinstance(directive, Directive),
            "Expected Directive but got %r" % directive,
        )

        _assert_valid_name(directive.name)

        # TODO: Ensure proper locations.
        argnames = set()
        for arg in directive.args:

            _assert(
                isinstance(arg, Argument),
                'Expected Argument in directive "@%s" but got "%s"'
                % (directive.name, arg),
            )

            _assert_valid_name(arg.name)

            _assert(
                arg.name not in argnames,
                'Duplicate argument "%s" on directive "@%s"'
                % (arg.name, directive.name),
            )

            _assert(
                is_input_type(arg.type),
                'Expected input type for argument "%s" on directive "@%s" '
                'but got "%s"' % (arg.name, directive.name, arg.type),
            )

            argnames.add(arg.name)


def validate_fields(schema, type_):
    """
    Args:
        schema (py_gql.schema.Schema):
        type_ (Union[py_gql.schema.ObjectType,py_gql.schema.InterfaceType]):
    """
    _assert(type_.fields, 'Type "%s" must define at least one field' % type_)
    fieldnames = set()
    for field in type_.fields:

        _assert(
            isinstance(field, Field),
            'Expected Field in "%s" but got "%s"' % (type_, field),
        )

        _assert_valid_name(field.name)

        _assert(
            field.name not in fieldnames,
            'Duplicate field "%s" on "%s"' % (field.name, type_),
        )

        _assert(
            is_output_type(field.type),
            'Expected output type for field "%s" on "%s" but got "%s"'
            % (field.name, type_, field.type),
        )

        argnames = set()

        for arg in field.args:

            _assert(
                isinstance(arg, Argument),
                'Expected Argument in "%s.%s" but got "%s"'
                % (type_, field.name, arg),
            )

            _assert_valid_name(arg.name)

            _assert(
                arg.name not in argnames,
                'Duplicate argument "%s" on "%s.%s"'
                % (arg.name, type_, field.name),
            )

            _assert(
                is_input_type(arg.type),
                'Expected input type for argument "%s" on "%s.%s" '
                'but got "%s"' % (arg.name, type_, field.name, arg.type),
            )

            argnames.add(arg.name)

        fieldnames.add(field.name)


def validate_interfaces(schema, type_):
    """
    Args:
        schema (py_gql.schema.Schema):
        type_ (py_gql.schema.ObjectType):
    """
    imlemented_types = set()
    for interface in type_.interfaces:
        _assert(
            isinstance(interface, InterfaceType),
            'Type "%s" mut only implement InterfaceType but got "%s"'
            % (type_, interface),
        )

        _assert(
            interface.name not in imlemented_types,
            'Type "%s" mut only implement interface "%s" once'
            % (type_, interface.name),
        )

        imlemented_types.add(interface.name)

        validate_implementation(schema, type_, interface)


def validate_implementation(schema, type_, interface):
    """
    Args:
        schema (py_gql.schema.Schema):
        type_ (py_gql.schema.ObjectType):
        interface (py_gql.schema.InterfaceType):
    """

    for field in interface.fields:
        object_field = type_.field_map.get(field.name, None)

        _assert(
            object_field is not None,
            'Interface field "%s.%s" is not implemented by type "%s"'
            % (interface.name, field.name, type_),
        )

        _assert(
            schema.is_subtype(object_field.type, field.type),
            'Interface field "%s.%s" expects type "%s" but '
            '"%s.%s" is type "%s"'
            % (
                interface.name,
                field.name,
                field.type,
                type_,
                field.name,
                object_field.type,
            ),
        )

        for arg in field.args:
            object_arg = object_field.arg_map.get(arg.name, None)

            _assert(
                object_arg is not None,
                'Interface field argument "%s.%s.%s" is not provided by '
                '"%s.%s"'
                % (
                    interface.name,
                    field.name,
                    arg.name,
                    type_.name,
                    field.name,
                ),
            )

            # TODO: Should this use is_subtype ?
            _assert(
                arg.type == object_arg.type,
                'Interface field argument "%s.%s.%s" expects type "%s" but '
                '"%s.%s.%s" is type "%s"'
                % (
                    interface.name,
                    field.name,
                    arg.name,
                    arg.type,
                    type_.name,
                    field.name,
                    arg.name,
                    object_arg.type,
                ),
            )

            # TODO: Validate default values

        for arg in object_field.args:
            interface_arg = field.arg_map.get(arg.name, None)
            if interface_arg is None:
                _assert(
                    not isinstance(arg.type, NonNullType),
                    'Object field argument "%s.%s.%s" is of required type '
                    '"%s" but is not provided by interface field "%s.%s"'
                    % (
                        type_.name,
                        field.name,
                        arg.name,
                        arg.type,
                        interface.name,
                        field.name,
                    ),
                )


def validate_union_members(schema, union_type):
    """
    Args:
        schema (py_gql.schema.Schema):
        union_type (py_gql.schema.UnionType):
    """
    _assert(
        union_type.types,
        'UnionType "%s" must at least define one member' % union_type,
    )

    member_types = set()
    for member_type in union_type.types:

        _assert(
            isinstance(member_type, ObjectType),
            'UnionType "%s" expects object types but got "%s"'
            % (union_type, member_type),
        )

        _assert(
            member_type.name not in member_types,
            'UnionType "%s" can only include type "%s" once'
            % (union_type, member_type),
        )

        member_types.add(member_type.name)


def validate_enum_values(schema, enum_type):
    """
    Args:
        schema (py_gql.schema.Schema):
        enum_type (py_gql.schema.EnumType)
    """
    _assert(
        enum_type.values,
        'EnumType "%s" must at least define one value' % enum_type,
    )

    for enum_value in enum_type.values:

        _assert(
            isinstance(enum_value, EnumValue),
            'Enum "%s" expects value to be EnumValue but got "%s"'
            % (enum_type, enum_value),
        )

        _assert_valid_name(enum_value.name)


def validate_input_fields(schema, input_object):
    """
    Args:
        schema (py_gql.schema.Schema):
        union_type (py_gql.schema.InputObjectType)
    """
    _assert(
        input_object.fields,
        'Type "%s" must define at least one field' % input_object,
    )

    fieldnames = set()

    for field in input_object.fields:

        _assert(
            isinstance(field, InputField),
            'Expected InputField in "%s" but got "%s"' % (input_object, field),
        )

        _assert(
            field.name not in fieldnames,
            'Duplicate field "%s" on "%s"' % (field.name, input_object),
        )

        _assert(
            is_input_type(field.type),
            'Expected input type for field "%s" on "%s" but got "%s"'
            % (field.name, input_object, field.type),
        )

        fieldnames.add(field.name)
