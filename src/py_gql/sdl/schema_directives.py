# -*- coding: utf-8 -*-
"""
Schema Directives

This is largely based on the way Apollo and graphql-tools implement it,
borrowing the same idea of using visitors and treating the schema as graph.
"""

from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .._utils import flatten
from ..exc import SDLError
from ..lang import ast as _ast
from ..schema import (
    SPECIFIED_DIRECTIVES,
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


SPECIFIED_DIRECTIVE_NAMES = [x.name for x in SPECIFIED_DIRECTIVES]


T = TypeVar("T")
TType = TypeVar("TType", bound=type)
TSchemaDirective = TypeVar("TSchemaDirective", bound=Type["SchemaDirective"])

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


class SchemaDirective(SchemaVisitor):
    """
    @directive implementation for use alongside  :func:`py_gql.schema.build_schema`.

    You need to subclass this in order to define your own custom directives.
    All valid directive locations have a corresponding `on_X` method to
    implement from :class:`~py_gql.schema.SchemaVisitor`.

    The definition attributes defines how the definition will be found at runtime.
    A `Directive` object defines the directive inline, while a string delegates
    to the schema at build time by name, in which case the directive must be
    part of the schema it's applied to.
    """

    definition = NotImplemented  # type: Union[Directive, str]

    def __init__(self, args=None):
        self.args = args or {}


def apply_schema_directives(
    schema: Schema,
    schema_directives: Sequence[TSchemaDirective],
) -> Schema:
    """
    Apply :class:`~py_gql.schema.SchemaDirective` implementers to a given schema.

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
        schema_directives: List of schema directives (`~py_gql.schema.SchemaDirective`).
            Each directive must implement the `definition` attribute.

    Returns:
        Modified schema.

    """
    return _SchemaDirectivesApplicationVisitor(
        schema_directives,
        schema.directives,
    ).on_schema(schema)


class _SchemaDirectivesApplicationVisitor(SchemaVisitor):
    def __init__(
        self,
        schema_directives: Sequence[TSchemaDirective],
        directives: Dict[str, Directive],
    ):

        self._defs = {}  # type: Dict[str, Tuple[Directive, TSchemaDirective]]

        for sd in schema_directives:
            if not isinstance(sd, type) or not issubclass(sd, SchemaDirective):
                raise TypeError(
                    f'Expected SchemaDirective subclass but got "{sd!r}"',
                )

            if isinstance(sd.definition, str):
                try:
                    self._defs[sd.definition] = directives[sd.definition], sd
                except KeyError:
                    raise SDLError(
                        "Unknown schema directive %s.\n"
                        "The definition attribute must either be an explicit "
                        "Directive instance or a string. When using a string, a "
                        "directive with that name must be present in the schema."
                        % sd.definition,
                    )
            else:
                self._defs[sd.definition.name] = sd.definition, sd

    def _collect_schema_directives(
        self,
        definition: _HasDirectives,
        loc: str,
    ) -> Iterator[SchemaDirective]:
        applied = set()  # type: Set[str]

        for node in _find_directives(definition):
            name = node.name.value

            if name in SPECIFIED_DIRECTIVE_NAMES:
                continue

            try:
                directive_def, schema_directive_cls = self._defs[name]
            except KeyError:
                raise SDLError(f'Unknown directive "@{name}"', [node])

            if loc not in directive_def.locations:
                raise SDLError(
                    f'Directive "@{name}" not applicable to "{loc}"',
                    [node],
                )

            if name in applied and not directive_def.repeatable:
                raise SDLError(f'Directive "@{name}" already applied', [node])

            args = coerce_argument_values(directive_def, node)
            applied.add(name)
            yield schema_directive_cls(args)

    def on_schema(self, schema: Schema) -> Schema:
        # Make sure the schema has all the definitions.
        schema.directives.update({n: d for n, (d, _) in self._defs.items()})

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
        self,
        input_object: InputObjectType,
    ) -> Optional[InputObjectType]:
        for sd in self._collect_schema_directives(input_object, "INPUT_OBJECT"):
            input_object = sd.on_input_object(input_object)  # type: ignore
            if input_object is None:
                return None
        return super().on_input_object(input_object)

    def on_input_field(self, field: InputField) -> Optional[InputField]:
        for sd in self._collect_schema_directives(
            field,
            "INPUT_FIELD_DEFINITION",
        ):
            field = sd.on_input_field(field)  # type: ignore
            if field is None:
                return None
        return super().on_input_field(field)
