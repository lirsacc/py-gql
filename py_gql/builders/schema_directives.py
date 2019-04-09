# -*- coding: utf-8 -*-
"""
Schema Directives
~~~~~~~~~~~~~~~~~

This is largely based on the way Apollo and grpahql-tools implement it,
borrowing the same idea of extending the AST visitor concept to the schema.
"""

from typing import (
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from .._utils import flatten
from ..exc import SDLError
from ..lang import ast as _ast
from ..schema import (
    SPECIFIED_SCALAR_TYPES,
    Argument,
    DeprecatedDirective,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputField,
    InputObjectType,
    InterfaceType,
    ObjectType,
    ScalarType,
    Schema,
    SchemaVisitor,
    UnionType,
)

__all__ = ("SchemaDirective", "apply_schema_directives")


T = TypeVar("T")
TType = TypeVar("TType", bound=type)

_HasDirectives = Union[
    Schema, GraphQLType, Field, Argument, InputField, EnumValue
]


def _find_directives(definition: _HasDirectives) -> List[_ast.Directive]:
    node = getattr(definition, "node", None)
    if node:
        return cast(_ast.SupportDirectives, node).directives or []

    nodes = getattr(definition, "nodes", [])
    return list(
        flatten(cast(_ast.SupportDirectives, n).directives for n in nodes if n)
    )


# REVIEW: With the definition and the usage as a keyed map we end up repeating
# the name of the directive.
class SchemaDirective(SchemaVisitor):
    """ @directive implementation for use alongside
    :func:`py_gql.schema.build_schema`.

    You need to subclass this in order to define your own custom directives.
    All valid directive locations have a corresponding `on_X` method to
    implement from :class:`~py_gql.schema.SchemaVisitor`.

    Attributes:
        definition (py_gql.schema.Directive): Corresponding directive definition.
    """

    definition = NotImplemented  # type: Directive

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

        for directive_name, schema_directive in schema_directives.items():

            if not issubclass(schema_directive, SchemaDirective):
                raise TypeError(
                    'Expected SchemaDirective subclass but got "%r"'
                    % schema_directive
                )

            if schema_directive.definition != NotImplemented:
                directive_definitions[
                    directive_name
                ] = schema_directive.definition

        for directive_name in directive_definitions:
            visitor_cls = schema_directives.get(directive_name)
            if visitor_cls is None:
                continue

        self._directive_definitions = directive_definitions

    def _collect_schema_directives(
        self, definition: _HasDirectives, loc: str
    ) -> Iterator[SchemaDirective]:
        from ..utilities import coerce_argument_values

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

    def on_field_definition(self, field: Field) -> Optional[Field]:
        for sd in self._collect_schema_directives(field, "FIELD_DEFINITION"):
            field = sd.on_field_definition(field)  # type: ignore
            if field is None:
                return None
        return super().on_field_definition(field)

    def on_argument_definition(self, arg: Argument) -> Optional[Argument]:
        for sd in self._collect_schema_directives(arg, "ARGUMENT_DEFINITION"):
            arg = sd.on_argument_definition(arg)  # type: ignore
            if arg is None:
                return None
        return super().on_argument_definition(arg)

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

    def on_input_field_definition(
        self, field: InputField
    ) -> Optional[InputField]:
        for sd in self._collect_schema_directives(
            field, "INPUT_FIELD_DEFINITION"
        ):
            field = sd.on_input_field_definition(field)  # type: ignore
            if field is None:
                return None
        return super().on_input_field_definition(field)


class DeprecatedSchemaDirective(SchemaDirective):
    """
    Implementation of the ``@deprecated`` schema directive to mark
    object / interface fields and enum values as deprecated when running
    introspection queries.

    Refer to :obj:`py_gql.schema.DeprecatedDirective` for details about the
    directive itself.
    """

    definition = DeprecatedDirective

    def on_field_definition(self, field: Field) -> Field:
        return Field(
            field.name,
            type_=field.type,
            args=field.arguments,
            description=field.description,
            deprecation_reason=self.args["reason"],
            resolver=field.resolver,
            node=field.node,
        )

    def on_enum_value(self, enum_value: EnumValue) -> EnumValue:
        return EnumValue(
            enum_value.name,
            enum_value.value,
            description=enum_value.description,
            deprecation_reason=self.args["reason"],
            node=enum_value.node,
        )
