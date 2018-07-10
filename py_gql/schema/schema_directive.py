# -*- coding: utf-8 -*-
""" Implement schema directives.
This is based of ther way Apollo graphql handles them which is in essence an
extension of the Visitor concept.
"""

import functools as ft

from . import types as _types
from .._utils import flatten
from ..exc import SDLError
from ..utilities import coerce_argument_values, default_resolver
from .directives import SPECIFIED_DIRECTIVES
from .schema import Schema

_SPECIFIED_NAMES = frozenset((d.name for d in SPECIFIED_DIRECTIVES))


class SchemaVisitor(object):
    """ Encode traversal and inline modification of a GraphQL schema.

    This assumes that the provided entities are part of a **valid** schema and
    doesn't revalidate this assumption.

    To encode custom behaviour, override the ``visit_*`` methods:

    - :meth:`visit_schema` should not return a modified schema and is expected
      to update the schema inline in order to avoid missing references issues
    - Other ``visit_**`` methods **must** return the modified object as None
      will remove them from their context (e.g. fields get removed from object,
      object removed from the schema, etc.).

    After modifying the schema you should use the :func:`heal_schema` helper to
    make sure all type references are correct and no type is missing.
    """

    def _visit_and_filter(self, iterator):
        return [
            value
            for value in (self.visit(entry) for entry in iterator)
            if value is not None
        ]

    def visit(self, entity):  # noqa : C901
        """ Actual visiting method. Do not override. """
        if isinstance(entity, Schema):
            # Do not replace the root of the schema
            self.visit_schema(entity)

            updated_types = {}
            for type_name, old_type in entity.types.items():
                if type_name.startswith("__"):
                    continue
                new_type = self.visit(old_type)
                if new_type is not None:
                    updated_types[new_type.name] = new_type

            for k, v in updated_types.items():
                entity.type_map[k] = v

            entity._rebuild_caches()
            return entity

        if isinstance(entity, _types.ObjectType):
            return self._visit_object(entity)
        elif isinstance(entity, _types.InterfaceType):
            return self._visit_interface(entity)
        elif isinstance(entity, _types.InputObjectType):
            return self._visit_input_object(entity)
        elif isinstance(entity, _types.ScalarType):
            return self.visit_scalar(entity)
        elif isinstance(entity, _types.UnionType):
            return self.visit_union(entity)
        elif isinstance(entity, _types.EnumType):
            return self._visit_enum(entity)
        elif isinstance(entity, _types.Field):
            return self._visit_field(entity)
        elif isinstance(entity, _types.Argument):
            return self.visit_argument(entity)
        elif isinstance(entity, _types.InputField):
            return self.visit_input_field(entity)
        elif isinstance(entity, _types.EnumValue):
            return self.visit_enum_value(entity)

        raise TypeError(type(entity))

    def _visit_object(self, object_type):
        new_type = self.visit_object(object_type)
        if new_type is not None:
            new_type.fields = self._visit_and_filter(new_type.fields)
        return new_type

    def _visit_interface(self, iface):
        new_type = self.visit_interface(iface)
        if new_type is not None:
            new_type.fields = self._visit_and_filter(new_type.fields)
        return new_type

    def _visit_field(self, field):
        new_field = self.visit_field(field)
        if new_field is not None:
            if new_field.args:
                new_field.args = self._visit_and_filter(new_field.args)
        return new_field

    def _visit_input_object(self, input_object):
        new_type = self.visit_input_object(input_object)
        if new_type is not None:
            new_type.fields = self._visit_and_filter(new_type.fields)
        return new_type

    def _visit_enum(self, enum):
        new_type = self.visit_enum(enum)
        return _types.EnumType(
            name=new_type.name,
            description=new_type.description,
            values=self._visit_and_filter(new_type.values.values()),
        )

    def default(self, x):
        return x

    # Override these methods to actualy do anything to the schema
    visit_schema = default
    visit_scalar = default
    visit_object = default
    visit_field = default
    visit_argument = default
    visit_interface = default
    visit_union = default
    visit_enum = default
    visit_enum_value = default
    visit_input_object = default
    visit_input_field = default


_CLS_TO_LOC = {
    Schema: "SCHEMA",
    _types.ScalarType: "SCALAR",
    _types.ObjectType: "OBJECT",
    _types.Field: "FIELD_DEFINITION",
    _types.Argument: "ARGUMENT_DEFINITION",
    _types.InterfaceType: "INTERFACE",
    _types.UnionType: "UNION",
    _types.EnumType: "ENUM",
    _types.EnumValue: "ENUM_VALUE",
    _types.InputObjectType: "INPUT_OBJECT",
    _types.InputField: "INPUT_FIELD_DEFINITION",
}


_LOCATION_TO_METHOD = {
    "SCHEMA": "visit_schema",
    "SCALAR": "visit_scalar",
    "OBJECT": "visit_object",
    "FIELD_DEFINITION": "visit_field",
    "ARGUMENT_DEFINITION": "visit_argument",
    "INTERFACE": "visit_interface",
    "UNION": "visit_union",
    "ENUM": "visit_enum",
    "ENUM_VALUE": "visit_enum_value",
    "INPUT_OBJECT": "visit_input_object",
    "INPUT_FIELD_DEFINITION": "visit_input_field",
}


def _find_directives(entity):
    node = getattr(entity, "node", None)
    if node:
        return entity.node.directives or []

    nodes = getattr(entity, "nodes", None)
    if nodes:
        return list(
            flatten(node.directives or [] for node in entity.nodes if node)
        )

    return []


class _HealSchemaVisitor(SchemaVisitor):
    """ Make sure internal representation of types match the ones in the
    schema's type map. """

    def __init__(self, schema):
        self.schema = schema

    def _healed(self, original):
        if isinstance(original, (_types.NonNullType, _types.ListType)):
            return type(original)(self._healed(original.type))
        return self.schema.get_type(original.name, original)

    def visit_schema(self, schema):
        if schema.query_type:
            schema.query_type = self._healed(schema.query_type)
        if schema.mutation_type:
            schema.mutation_type = self._healed(schema.mutation_type)
        if schema.subscription_type:
            schema.subscription_type = self._healed(schema.subscription_type)

    def visit_object(self, object_definition):
        object_definition.interfaces = [
            self._healed(iface) for iface in object_definition.interfaces
        ]
        return object_definition

    def visit_field(self, field_definition):
        field_definition.type = self._healed(field_definition.type)
        return field_definition

    def visit_argument(self, argument_definition):
        argument_definition.type = self._healed(argument_definition.type)
        return argument_definition

    def visit_union(self, union):
        union.types = [self._healed(t) for t in union.types]
        return union

    def visit_input_field(self, input_field):
        input_field.type = self._healed(input_field.type)
        return input_field


class _SchemaDirectivesApplicator(SchemaVisitor):
    def __init__(self, schema, schema_directives, strict=False):
        self._schema = schema
        self._schema_directives = schema_directives
        self._strict = strict

        assert isinstance(schema, Schema)

        directive_definitions = dict(schema.directives)  # Shallow copy
        for directive_name, schema_directive in schema_directives.items():
            assert issubclass(schema_directive, SchemaDirective)
            if schema_directive.definition:
                directive_definitions[
                    directive_name
                ] = schema_directive.definition

        for directive_name, definition in directive_definitions.items():
            visitor_cls = schema_directives.get(directive_name)
            if visitor_cls is None:
                continue

            for loc in definition.locations:
                if not visitor_cls.support_location(loc):
                    raise SDLError(
                        "SchemaDirective implementation for @%s must support %s"
                        % (directive_name, loc)
                    )

        self._directive_definitions = directive_definitions

    def default(self, entity):
        for directive_node in _find_directives(entity):
            name = directive_node.name.value
            directive_def = self._directive_definitions.get(name)
            if directive_def is None:
                raise SDLError(
                    'Unknown directive "@%s' % name, [directive_node]
                )

            schema_directive = self._schema_directives.get(name)
            if schema_directive is None:
                if name not in _SPECIFIED_NAMES and self._strict:
                    raise SDLError(
                        'Missing directive implementation for "@%s"' % name
                    )
                continue

            loc = _CLS_TO_LOC.get(type(entity))
            if loc not in directive_def.locations:
                raise SDLError(
                    'Directive "@%s" not applicable to "%s"' % (name, loc),
                    [directive_node],
                )

            args = coerce_argument_values(directive_def, directive_node)
            entity = schema_directive(args).visit(entity)

        return entity

    visit_schema = default
    visit_scalar = default
    visit_object = default
    visit_field = default
    visit_argument = default
    visit_interface = default
    visit_union = default
    visit_enum = default
    visit_enum_value = default
    visit_input_object = default
    visit_input_field = default


class SchemaDirective(SchemaVisitor):
    """ @directive implementation for use alongside
    :func:`py_gql.schema.schema_from_ast`.

    You need to subclass this in order to define your own custom directives.
    """

    definition = None

    def __init__(self, args=None):
        self.args = args

    @classmethod
    def support_location(cls, location):
        mtd = getattr(cls, _LOCATION_TO_METHOD[location], None)
        return callable(mtd) and mtd != cls.default


def wrap_resolver(field_def, func):
    """ Apply a modificator function on the resolver of a given field
    definition.

    If no original resolver is set, this use the default resolver.

    :type field_def: py_gql.schema.Field
    :param field_def: Field defnition to modify

    :type func: callable
    :param func: Function to call on the result of the resolver
    """
    source_resolver = field_def.resolve or default_resolver

    @ft.wraps(source_resolver)
    def resolver(parent_value, args, context, info):
        value = source_resolver(parent_value, args, context, info)
        if value is None:
            return value
        return func(value)

    field_def.resolve = resolver
    return field_def


def heal_schema(schema):
    """ Correct type reference in a schema.

    :type schema: py_gql.schema.Schema
    :param schema: Schema to correct

    .. warning::

        This can modify the types inline and is expected to be used after
        generating a schema programatically. Do not use this if your types are
        globally defined.
    """
    _HealSchemaVisitor(schema).visit(schema)


def apply_schema_directives(schema, schema_directives, strict=False):
    """ Apply schema directives to a schema

    :type schema: py_gql.schema.Schema
    :param schema:

    :type schema_directives: Mapping[str, type]
    :param schema_directives: ``{ name -> SchemaDirective subclass }``
        Schema directives are instantiated and provided the arguments
        for each occurence so user need to provide classes.

    :type strict: bool
    :param strict:
        If ``True`` will raise on missing implementation, otherwise silently
        ignores these directivess

    :rtype: py_gql.schema.Schema
    :returns: Updated schema
    """
    _SchemaDirectivesApplicator(schema, schema_directives, strict=strict).visit(
        schema
    )
    heal_schema(schema)
    schema.validate()
