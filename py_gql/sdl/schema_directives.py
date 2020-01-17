# -*- coding: utf-8 -*-
"""
Schema Directives
~~~~~~~~~~~~~~~~~

This is largely based on the way Apollo and graphql-tools implement it,
borrowing the same idea of using visitors and treating the schema as graph.
"""

from typing import Iterator, List, Mapping, Optional, Set, Type, TypeVar, Union

from .._utils import flatten
from ..exc import SDLError
from ..lang import ast as _ast
from ..schema import (
    SPECIFIED_SCALAR_TYPES,
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    InputField,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    Schema,
    SchemaVisitor,
    UnionType,
)
from ..utilities import coerce_argument_values

__all__ = ("SchemaDirective", "apply_schema_directives")


T = TypeVar("T")
TType = TypeVar("TType", bound=type)

_HasDirectives = Union[
    Argument,
    EnumType,
    EnumValue,
    Field,
    InputField,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    Schema,
    UnionType,
]


def _find_directives(definition: _HasDirectives) -> List[_ast.Directive]:
    if isinstance(definition, (Field, Argument, InputField, EnumValue)):
        return definition.node.directives if definition.node is not None else []
    else:
        return list(flatten(n.directives for n in definition.nodes if n))


# REVIEW: With the definition and the usage as a keyed map we end up repeating
# the name of the directive.
class SchemaDirective(SchemaVisitor):
    """
    @directive implementation for use alongside  :func:`py_gql.schema.build_schema`.

    You need to subclass this in order to define your own custom directives.
    All valid directive locations have a corresponding `on_X` method to
    implement from :class:`~py_gql.schema.SchemaVisitor`.
    """

    def __init__(self, args=None):
        self.args = args or {}


def apply_schema_directives(
    schema: Schema, schema_directives: Mapping[str, Type[SchemaDirective]]
) -> Schema:
    """
    Apply :class:`~py_gql.schema.SchemaDirective` implementors to a given schema.

    This assumes the provided schema was built from a GraphQL document and
    contains references to the parse node which contains the actual directive
    information.

    Each directive will be instantiated with the arguments extracted from the
    parse nodes (which is why we need to provide a class here and not an
    instance of :class:`~py_gql.schema.SchemaDirective`).

    Warning:
        Specified types (scalars, introspection) cannot be modified through
        schema directives.

    Args:
        schema: Schema to modify

        schema_directives:
            Dict of directive name to corredponsing
            :class:`~py_gql.schema.SchemaDirective` implementation. The directive
            must either be defined in the schema or the class implement the
            `definition` attribute.
    """
    return _SchemaDirectivesApplicationVisitor(
        schema.directives, schema_directives
    ).on_schema(schema)


class _SchemaDirectivesApplicationVisitor(SchemaVisitor):
    def __init__(
        self,
        directive_definitions: Mapping[str, Directive],
        schema_directives: Mapping[str, Type[SchemaDirective]],
    ):
        self._schema_directives = schema_directives
        directive_definitions = dict(directive_definitions)

        for schema_directive in schema_directives.values():
            if not issubclass(schema_directive, SchemaDirective):
                raise TypeError(
                    'Expected SchemaDirective subclass but got "%r"'
                    % schema_directive
                )

        for directive_name in directive_definitions:
            visitor_cls = schema_directives.get(directive_name)
            if visitor_cls is None:
                continue

        self._directive_definitions = directive_definitions

    def _collect_schema_directives(
        self, definition: _HasDirectives, loc: str
    ) -> Iterator[SchemaDirective]:
        applied = set()  # type: Set[str]

        for node in _find_directives(definition):
            name = node.name.value
            try:
                directive_def = self._directive_definitions[name]
            except KeyError:
                raise SDLError('Unknown directive "@%s' % name, [node])

            try:
                schema_directive_cls = self._schema_directives[name]
            except KeyError:
                raise SDLError('Missing implementation for "@%s"' % name)

            if loc not in directive_def.locations:
                raise SDLError(
                    'Directive "@%s" not applicable to "%s"' % (name, loc),
                    [node],
                )

            if name in applied:
                raise SDLError('Directive "@%s" already applied' % name, [node])

            args = coerce_argument_values(directive_def, node)
            applied.add(name)
            yield schema_directive_cls(args)

    def on_schema(self, schema: Schema) -> Schema:
        for sd in self._collect_schema_directives(schema, "SCHEMA"):
            schema = sd.on_schema(schema)
        return super().on_schema(schema)

    def on_scalar(self, scalar: ScalarType) -> Optional[ScalarType]:
        if scalar in SPECIFIED_SCALAR_TYPES:
            return scalar

        for sd in self._collect_schema_directives(scalar, "SCALAR"):
            scalar = sd.on_scalar(scalar)  # type: ignore
            if scalar is None:
                return None
        return super().on_scalar(scalar)

    def on_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        for sd in self._collect_schema_directives(object_type, "OBJECT"):
            object_type = sd.on_object(object_type)  # type: ignore
            if object_type is None:
                return object_type
        return super().on_object(object_type)

    def on_field(self, field: Field) -> Optional[Field]:
        for sd in self._collect_schema_directives(field, "FIELD_DEFINITION"):
            field = sd.on_field(field)  # type: ignore
            if field is None:
                return None
        return super().on_field(field)

    def on_argument(self, arg: Argument) -> Optional[Argument]:
        for sd in self._collect_schema_directives(arg, "ARGUMENT_DEFINITION"):
            arg = sd.on_argument(arg)  # type: ignore
            if arg is None:
                return None
        return super().on_argument(arg)

    def on_interface(self, interface: InterfaceType) -> Optional[InterfaceType]:
        for sd in self._collect_schema_directives(interface, "INTERFACE"):
            interface = sd.on_interface(interface)  # type: ignore
            if interface is None:
                return None
        return super().on_interface(interface)

    def on_union(self, union: UnionType) -> Optional[UnionType]:
        for sd in self._collect_schema_directives(union, "UNION"):
            union = sd.on_union(union)  # type: ignore
            if union is None:
                return None
        return super().on_union(union)

    def on_enum(self, enum: EnumType) -> Optional[EnumType]:
        for sd in self._collect_schema_directives(enum, "ENUM"):
            enum = sd.on_enum(enum)  # type: ignore
            if enum is None:
                return None
        return super().on_enum(enum)

    def on_enum_value(self, enum_value: EnumValue) -> Optional[EnumValue]:
        for sd in self._collect_schema_directives(enum_value, "ENUM_VALUE"):
            enum_value = sd.on_enum_value(enum_value)  # type: ignore
            if enum_value is None:
                return None
        return super().on_enum_value(enum_value)

    def on_input_object(
        self, input_object: InputObjectType
    ) -> Optional[InputObjectType]:
        for sd in self._collect_schema_directives(input_object, "INPUT_OBJECT"):
            input_object = sd.on_input_object(input_object)  # type: ignore
            if input_object is None:
                return None
        return super().on_input_object(input_object)

    def on_input_field(self, field: InputField) -> Optional[InputField]:
        for sd in self._collect_schema_directives(
            field, "INPUT_FIELD_DEFINITION"
        ):
            field = sd.on_input_field(field)  # type: ignore
            if field is None:
                return None
        return super().on_input_field(field)
