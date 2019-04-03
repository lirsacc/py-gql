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
from ..utilities import coerce_argument_values
from .directives import SPECIFIED_DIRECTIVES, DeprecatedDirective
from .fix_type_references import fix_type_references
from .scalars import SPECIFIED_SCALAR_TYPES
from .schema import Schema
from .schema_visitor import SchemaVisitor
from .types import (
    Argument,
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
    UnionType,
)

__all__ = ("SchemaDirective", "apply_schema_directives")

_SPECIFIED_DIRECTIVE_NAMES = frozenset(d.name for d in SPECIFIED_DIRECTIVES)


T = TypeVar("T")
GT = TypeVar("GT", bound=GraphQLType)
AT = TypeVar("AT", bound=type)

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
    For example a directive that modifies the field resolver to always
    uppercase the result would look like this:

    .. code-block:: python

        class UppercaseDirective(SchemaDirective):

        def visit_field(self, field_definition):
            assert field_definition.type is String
            return Field(
                field_definition.name,
                field_definition.type,
                args=field_definition.args,
                description=field_definition.description,
                deprecation_reason=field_definition.deprecation_reason,
                resolver=lambda *a, **kw: field_definition.resolver(*a, **kw).upper(),
                node=field_definition.node,
            )

        # Use it as follows
        schema = build_schema(
            '''
            directive @upper on FIELD_DEFINITION

            type Query {
                foo: String @upper
            }
            ''',
            schema_directives={
                'upper': UppercaseDirective
            }
        )

    Warning:
        While this is aimed to be used after
        :func:`~py_gql.schema.build_schema` and its derivatives,
        schema directives can modify types inline. In case you use globally
        defined type definitions this can have some nasty side effects and so
        it is encouraged to return new type definitions instead.

    Warning:
        Specified types (scalars, introspection) cannot be modified through
        schema directives.
    """

    definition = NotImplemented  # type: Directive

    def __init__(self, args=None):
        self.args = args


def apply_schema_directives(
    schema: Schema,
    schema_directives: Mapping[str, Type[SchemaDirective]],
    strict: bool = False,
) -> Schema:
    """ Apply `SchemaDirective` classes to a given schema.
    """
    return fix_type_references(
        _SchemaDirectivesApplicationVisitor(
            schema.directives, schema_directives, strict
        ).visit_schema(schema)
    )


class _SchemaDirectivesApplicationVisitor(SchemaVisitor):
    def __init__(
        self,
        directive_definitions: Mapping[str, Directive],
        schema_directives: Mapping[str, Type[SchemaDirective]],
        strict: bool = False,
    ):
        self._schema_directives = schema_directives
        self._strict = strict
        directive_definitions = dict(directive_definitions)

        for directive_name, schema_directive in schema_directives.items():
            assert issubclass(schema_directive, SchemaDirective)
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
                if name not in _SPECIFIED_DIRECTIVE_NAMES and self._strict:
                    raise SDLError('Missing implementation for "@%s"' % name)
                continue

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

    def visit_schema(self, schema: Schema) -> Schema:
        for sd in self._collect_schema_directives(schema, "SCHEMA"):
            schema = sd.visit_schema(schema)
        return super().visit_schema(schema)

    def visit_scalar(self, scalar: ScalarType[AT]) -> Optional[ScalarType[AT]]:
        if scalar in SPECIFIED_SCALAR_TYPES:
            return scalar

        for sd in self._collect_schema_directives(scalar, "SCALAR"):
            scalar = sd.visit_scalar(scalar)  # type: ignore
            if scalar is None:
                return None
        return super().visit_scalar(scalar)

    def visit_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        for sd in self._collect_schema_directives(object_type, "OBJECT"):
            object_type = sd.visit_object(object_type)  # type: ignore
            if object_type is None:
                return object_type
        return super().visit_object(object_type)

    def visit_field(self, field: Field) -> Optional[Field]:
        for sd in self._collect_schema_directives(field, "FIELD_DEFINITION"):
            field = sd.visit_field(field)  # type: ignore
            if field is None:
                return None
        return super().visit_field(field)

    def visit_argument(self, arg: Argument) -> Optional[Argument]:
        for sd in self._collect_schema_directives(arg, "ARGUMENT_DEFINITION"):
            arg = sd.visit_argument(arg)  # type: ignore
            if arg is None:
                return None
        return super().visit_argument(arg)

    def visit_interface(
        self, interface: InterfaceType
    ) -> Optional[InterfaceType]:
        for sd in self._collect_schema_directives(interface, "INTERFACE"):
            interface = sd.visit_interface(interface)  # type: ignore
            if interface is None:
                return None
        return super().visit_interface(interface)

    def visit_union(self, union: UnionType) -> Optional[UnionType]:
        for sd in self._collect_schema_directives(union, "UNION"):
            union = sd.visit_union(union)  # type: ignore
            if union is None:
                return None
        return super().visit_union(union)

    def visit_enum(self, enum: EnumType) -> Optional[EnumType]:
        for sd in self._collect_schema_directives(enum, "ENUM"):
            enum = sd.visit_enum(enum)  # type: ignore
            if enum is None:
                return None
        return super().visit_enum(enum)

    def visit_enum_value(self, enum_value: EnumValue) -> Optional[EnumValue]:
        for sd in self._collect_schema_directives(enum_value, "ENUM_VALUE"):
            enum_value = sd.visit_enum_value(enum_value)  # type: ignore
            if enum_value is None:
                return None
        return super().visit_enum_value(enum_value)

    def visit_input_object(
        self, input_object: InputObjectType
    ) -> Optional[InputObjectType]:
        for sd in self._collect_schema_directives(input_object, "INPUT_OBJECT"):
            input_object = sd.visit_input_object(input_object)  # type: ignore
            if input_object is None:
                return None
        return super().visit_input_object(input_object)

    def visit_input_field(self, field: InputField) -> Optional[InputField]:
        for sd in self._collect_schema_directives(
            field, "INPUT_FIELD_DEFINITION"
        ):
            field = sd.visit_input_field(field)  # type: ignore
            if field is None:
                return None
        return super().visit_input_field(field)


class DeprecatedSchemaDirective(SchemaDirective):
    """ Implementation of the ``@deprecated`` schema directive. """

    definition = DeprecatedDirective

    def visist_field(self, field: Field) -> Field:
        return Field(
            field.name,
            type_=field.type,
            args=field.arguments,
            description=field.description,
            deprecation_reason=self.args["reason"],
            resolver=field.resolver,
            node=field.node,
        )

    def visist_enum_value(self, enum_value: EnumValue) -> EnumValue:
        return EnumValue(
            enum_value.name,
            enum_value.value,
            description=enum_value.description,
            deprecation_reason=self.args["reason"],
            node=enum_value.node,
        )
