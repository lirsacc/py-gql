# -*- coding: utf-8 -*-
""" Implement schema directives.
This is based of ther way Apollo graphql handles them which is in essence an
extension of the Visitor concept.
"""

import functools as ft

from . import types as _schema
from ..exc import SDLError
from ..utilities import default_resolver, directive_arguments
from .schema import Schema


def _apply_and_filter(iterator, func):
    return [value for value in (func(entry) for entry in iterator) if value is not None]


class _SchemaVisitor(object):
    """ Encode traversal and modification of a GraphQL schema """

    def __call__(self, entity):
        if isinstance(entity, Schema):
            print(entity)
            # Do not replace the root of the schema
            self.visit_schema(entity)

            updated_types = {}

            for type_name, old_type in entity.types.items():
                if type_name.startswith("__"):
                    continue
                new_type = self(old_type)
                print(old_type, new_type)
                if new_type is not None:
                    updated_types[new_type.name] = old_type

            entity.types = updated_types
            return entity

        if isinstance(entity, _schema.ObjectType):
            return self._visit_object(entity)
        elif isinstance(entity, _schema.InterfaceType):
            return self._visit_interface(entity)
        elif isinstance(entity, _schema.InputObjectType):
            return self._visit_input_object(entity)
        elif isinstance(entity, _schema.ScalarType):
            return self.visit_scalar(entity)
        elif isinstance(entity, _schema.UnionType):
            return self.visit_union(entity)
        elif isinstance(entity, _schema.EnumType):
            return self._visit_enum(entity)
        raise TypeError(old_type(entity))

    def _visit_object(self, object_type):
        print(object_type)
        new_type = self.visit_object(object_type)
        if new_type is not None:
            new_type.fields = _apply_and_filter(new_type.fields, self._visit_field)
        return new_type

    def _visit_interface(self, iface):
        new_type = self.visit_interface(iface)
        if new_type is not None:
            new_type.fields = _apply_and_filter(new_type.fields, self._visit_field)
        return new_type

    def _visit_field(self, field):
        print(field.name, field.resolve)
        new_field = self.visit_field(field)
        print(new_field.name, new_field.resolve)
        if new_field is not None:
            if new_field.args:
                new_field.args = _apply_and_filter(new_field.args, self.visit_argument)
        return new_field

    def _visit_input_object(self, input_object):
        new_type = self.visit_input_object(input_object)
        if new_type is not None:
            new_type.fields = _apply_and_filter(new_type.fields, self.visit_input_field)
        return new_type

    def _visit_enum(self, enum):
        new_type = self.visit_enum(enum)
        return _schema.EnumType(
            name=new_type.name,
            description=new_type.description,
            values=_apply_and_filter(new_type.values, self.visit_enum_value),
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
    _schema.ScalarType: "SCALAR",
    _schema.ObjectType: "OBJECT",
    _schema.Field: "FIELD_DEFINITION",
    _schema.Argument: "ARGUMENT_DEFINITION",
    _schema.InterfaceType: "INTERFACE",
    _schema.UnionType: "UNION",
    _schema.UnionType: "ENUM",
    _schema.EnumValue: "ENUM_VALUE",
    _schema.InputObjectType: "INPUT_OBJECT",
    _schema.InputField: "INPUT_FIELD_DEFINITION",
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


class SchemaDirectivesApplicator(_SchemaVisitor):
    def __init__(self, schema, schema_directives, variables=None):
        self._schema = schema
        self._schema_directives = schema_directives
        self._variables = variables

        assert isinstance(schema, Schema)
        assert all(issubclass(sd, SchemaDirective) for sd in schema_directives.values())

        directive_definitions = dict(schema.directives)  # Shallow copy
        for directive_name, schema_directive in schema_directives.items():
            if schema_directive.definition:
                directive_definitions[directive_name] = schema_directive.definition

        for directive_name, definition in directive_definitions.items():
            visitor_cls = schema_directives.get(directive_name)
            if visitor_cls is None:
                continue

            for loc in definition.locations:
                if not visitor_cls.support_location(loc):
                    raise SDLError(
                        "SchemaDirective for @%s must support %s"
                        % (directive_name, loc)
                    )

        self._directive_definitions = directive_definitions

    def default(self, entity):
        print("SDA", entity, entity.node)
        if entity.node is None:
            return entity

        for directive_node in entity.node.directives:
            name = directive_node.name.value
            print("@", name)
            directive_def = self._directive_definitions.get(name)
            if directive_def is None:
                raise SDLError('Unknown directive "@%s' % name, directive_node)

            schema_directive = self._schema_directives.get(name)
            if schema_directive is None:
                continue

            loc = _CLS_TO_LOC.get(type(entity))
            if loc not in directive_def.locations:
                raise SDLError(
                    'Directive "@%s" not applicable to "%s"' % (name, loc),
                    directive_node,
                )

            args = directive_arguments(directive_def, directive_node, self._variables)
            entity = schema_directive(args)(entity)

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


class SchemaDirective(_SchemaVisitor):
    """ @directive implementation for use in the SDL and `schema_from_ast`.
    """

    definition = None

    def __init__(self, arguments=None):
        self.arguments = arguments

    @classmethod
    def support_location(cls, location):
        mtd = getattr(cls, _LOCATION_TO_METHOD[location], None)
        return callable(mtd) and mtd is not cls.default


class UppercaseDirective(SchemaDirective):

    definition = _schema.Directive("upper", ["FIELD_DEFINITION"])

    def visit_field(self, field_definition):

        print("DO", field_definition)
        assert False

        source_resolver = field_definition.resolve or default_resolver

        @ft.wraps(source_resolver)
        def resolver(parent_value, args, context, info):
            print("CUSTOM RESOLVER")
            value = source_resolver(parent_value, args, context, info)
            print(value)
            if value is None:
                return value
            return value.upper()

        field_definition.resolve = resolver
        return field_definition


def apply_schema_directives(schema, schema_directives):
    """
    """
    visit = SchemaDirectivesApplicator(schema, schema_directives)
    return visit(schema)
