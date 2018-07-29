# -*- coding: utf-8 -*-
""" Implement schema directives.
This is based of ther way Apollo graphql handles them which is in essence an
extension of the Visitor concept.
"""

from .. import types as _types
from ..._utils import flatten
from ...exc import SDLError
from ...utilities import coerce_argument_values
from ..directives import SPECIFIED_DIRECTIVES
from ..scalars import DefaultScalarType
from ..schema import Schema

_SPECIFIED_NAMES = frozenset((d.name for d in SPECIFIED_DIRECTIVES))


def visit_schema(visitor, schema):
    """ Traverse a schema based on a visitor instance.

    Args:
        visitor (SchemaVisitor): Visitor to use
        schema (py_gql.schema.Schema): Schema to visit

    Returns:
        py_gql.schema.Schema:
    """
    visitor.visit_schema(schema)

    updated_types = {}
    for type_name, old_type in schema.types.items():
        if type_name.startswith("__"):
            continue
        new_type = _visit(visitor, old_type)
        if new_type is not None and new_type is not old_type:
            updated_types[type_name] = new_type

    if updated_types:
        for k, v in updated_types.items():
            schema.type_map[k] = v
        schema._rebuild_caches()

    return schema


def _visit_and_filter(visitor, iterator):
    # type: (Visitor, Iterator[T]) -> List[T]
    visited = (_visit(visitor, entry) for entry in iterator)
    return [value for value in visited if value is not None]


def _visit(visitor, entity):
    # type: (Visitor, T) -> Optional[T]
    if isinstance(entity, Schema):
        return visit_schema(visitor, entity)
    elif isinstance(entity, _types.ObjectType):
        return _visit_object(visitor, entity)
    elif isinstance(entity, _types.InterfaceType):
        return _visit_interface(visitor, entity)
    elif isinstance(entity, _types.InputObjectType):
        return _visit_input_object(visitor, entity)
    elif isinstance(entity, _types.ScalarType):
        return visitor.visit_scalar(entity)
    elif isinstance(entity, _types.UnionType):
        return visitor.visit_union(entity)
    elif isinstance(entity, _types.EnumType):
        return _visit_enum(visitor, entity)
    elif isinstance(entity, _types.Field):
        return _visit_field(visitor, entity)
    elif isinstance(entity, _types.Argument):
        return visitor.visit_argument(entity)
    elif isinstance(entity, _types.InputField):
        return visitor.visit_input_field(entity)
    elif isinstance(entity, _types.EnumValue):
        return visitor.visit_enum_value(entity)

    raise TypeError(type(entity))


def _visit_object(visitor, object_type):
    # type: (Visitor, py_gql.schema.ObjectType) -> Optional[py_gql.schema.ObjectType]
    new_type = visitor.visit_object(object_type)
    if new_type is not None:
        new_type.fields = _visit_and_filter(visitor, new_type.fields)
    return new_type


def _visit_interface(visitor, iface):
    # type: (
    #   Visitor,
    #   py_gql.schema.InterfaceType
    # ) -> Optional[py_gql.schema.InterfaceType]
    new_type = visitor.visit_interface(iface)
    if new_type is not None:
        new_type.fields = _visit_and_filter(visitor, new_type.fields)
    return new_type


def _visit_field(visitor, field):
    # type: (Visitor, py_gql.schema.Field) -> Optional[py_gql.schema.Field]
    new_field = visitor.visit_field(field)
    if new_field is not None:
        if new_field.args:
            new_field.args = _visit_and_filter(visitor, new_field.args)
    return new_field


def _visit_input_object(visitor, input_object):
    # type: (
    #   Visitor,
    #   py_gql.schema.InputObjectType
    # ) -> Optional[py_gql.schema.InputObjectType]
    new_type = visitor.visit_input_object(input_object)
    if new_type is not None:
        new_type.fields = _visit_and_filter(visitor, new_type.fields)
    return new_type


def _visit_enum(visitor, enum):
    # type: (Visitor, py_gql.schema.EnumType) -> Optional[py_gql.schema.EnumType]
    new_type = visitor.visit_enum(enum)
    return _types.EnumType(
        name=new_type.name,
        description=new_type.description,
        values=_visit_and_filter(visitor, new_type.values.values()),
    )


class SchemaVisitor(object):
    """ Base class to encode schema traversal and inline modifications.

    Subclass and override the ``visit_*`` methods to implement custom behaviour.
    """

    def visit(self, entity):
        return _visit(self, entity)

    def default(self, x):
        return x

    # Override these methods to actually do anything to the schema
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
    DefaultScalarType: "SCALAR",
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
    nodes = getattr(entity, "nodes", [])
    return list(flatten(node.directives or [] for node in nodes if node))


class HealSchemaVisitor(SchemaVisitor):
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
        applied = set()
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

            if name in applied:
                raise SDLError(
                    'Directive "@%s" already applied' % name, [directive_node]
                )

            args = coerce_argument_values(directive_def, directive_node)
            entity = _visit(schema_directive(args), entity)
            applied.add(directive_def.name)

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
