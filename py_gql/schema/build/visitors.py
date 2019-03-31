# -*- coding: utf-8 -*-
""" Implement schema directives.
This is based of ther way Apollo graphql handles them which is in essence an
extension of the Visitor concept.
"""

from typing import (
    Callable,
    Iterable,
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

from ..._utils import flatten
from ...exc import SDLError
from ...lang import ast as _ast
from ...utilities import coerce_argument_values
from ..directives import SPECIFIED_DIRECTIVES
from ..scalars import SPECIFIED_SCALAR_TYPES
from ..schema import Schema
from ..types import (
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLType,
    InputField,
    InputObjectType,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    ScalarType,
    UnionType,
)

_SPECIFIED_DIRECTIVE_NAMES = frozenset(d.name for d in SPECIFIED_DIRECTIVES)


T = TypeVar("T")
GT = TypeVar("GT", bound=GraphQLType)
AT = TypeVar("AT", bound=type)

_HasDirectives = Union[
    Schema, GraphQLType, Field, Argument, InputField, EnumValue
]


def _map_and_filter(
    func: Callable[[T], Optional[T]], iterator: Iterable[T]
) -> List[T]:
    return [
        value
        for value in (func(entry) for entry in iterator)
        if value is not None
    ]


def _find_directives(definition: _HasDirectives) -> List[_ast.Directive]:
    node = getattr(definition, "node", None)
    if node:
        return cast(_ast.SupportDirectives, node).directives or []

    nodes = getattr(definition, "nodes", [])
    return list(
        flatten(cast(_ast.SupportDirectives, n).directives for n in nodes if n)
    )


class SchemaVisitor(object):
    """ Base class to encode schema traversal and inline modifications.

    Subclass and override the ``visit_*`` methods to implement custom behaviour.
    All visitor methods *must* return the modified value; returning ``None``
    will drop the respective values from their context.
    """

    def visit_schema(self, schema: Schema) -> Schema:
        updated_types = {}

        for type_name, original in schema.types.items():
            if type_name.startswith("__") or original in SPECIFIED_SCALAR_TYPES:
                continue

            if isinstance(original, ObjectType):
                updated = self.visit_object(
                    original
                )  # type: Optional[GraphQLType]
            elif isinstance(original, InterfaceType):
                updated = self.visit_interface(original)
            elif isinstance(original, InputObjectType):
                updated = self.visit_input_object(original)
            elif isinstance(original, ScalarType):
                updated = self.visit_scalar(original)
            elif isinstance(original, UnionType):
                updated = self.visit_union(original)
            elif isinstance(original, EnumType):
                updated = self.visit_enum(original)
            elif isinstance(original, Field):
                updated = self.visit_field(original)
            else:
                raise TypeError(type(original))

            if updated is not None and updated is not original:
                updated_types[type_name] = updated

        if not updated_types:
            return schema

        for k, v in updated_types.items():
            schema.type_map[k] = v

        schema.query_type = cast(
            ObjectType,
            (
                updated_types.get(schema.query_type.name, schema.query_type)
                if schema.query_type
                else None
            ),
        )

        schema.mutation_type = cast(
            ObjectType,
            (
                updated_types.get(
                    schema.mutation_type.name, schema.mutation_type
                )
                if schema.mutation_type
                else None
            ),
        )

        schema.subscription_type = cast(
            ObjectType,
            (
                updated_types.get(
                    schema.subscription_type.name, schema.subscription_type
                )
                if schema.subscription_type
                else None
            ),
        )

        schema._rebuild_caches()

        return schema

    def visit_scalar(self, scalar: ScalarType[AT]) -> Optional[ScalarType[AT]]:
        return scalar

    def visit_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        updated_fields = _map_and_filter(self.visit_field, object_type.fields)
        if updated_fields != object_type.fields:
            object_type._fields = updated_fields
        return object_type

    def visit_field(self, field: Field) -> Optional[Field]:
        updated_args = _map_and_filter(self.visit_argument, field.arguments)
        if updated_args != field.arguments:
            field._args = updated_args
        return field

    def visit_argument(self, argument: Argument) -> Optional[Argument]:
        return argument

    def visit_interface(
        self, interface: InterfaceType
    ) -> Optional[InterfaceType]:
        updated_fields = _map_and_filter(self.visit_field, interface.fields)
        if updated_fields != interface.fields:
            interface._fields = updated_fields
        return interface

    def visit_union(self, union: UnionType) -> Optional[UnionType]:
        return union

    def visit_enum(self, enum: EnumType) -> Optional[EnumType]:
        updated_values = _map_and_filter(self.visit_enum_value, enum.values)
        if updated_values != enum.values:
            enum._set_values(updated_values)
        return enum

    def visit_enum_value(self, enum_value: EnumValue) -> Optional[EnumValue]:
        return enum_value

    def visit_input_object(
        self, input_object: InputObjectType
    ) -> Optional[InputObjectType]:
        updated_fields = _map_and_filter(
            self.visit_input_field, input_object.fields
        )
        if updated_fields != input_object.fields:
            input_object._fields = updated_fields
        return input_object

    def visit_input_field(self, field: InputField) -> Optional[InputField]:
        return field


# REVIEW: With the definition and the usage as a keyed map we end up repeating
# the name of the directive.
class SchemaDirective(SchemaVisitor):
    """ @directive implementation for use alongside
    :func:`py_gql.schema.build.build_schema`.

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
        :func:`~py_gql.schema.build.build_schema_from_ast` and its derivatives,
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


class SchemaDirectivesApplicationVisitor(SchemaVisitor):
    """ Used to apply multiple SchemaDirectives to a schema. """

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


class HealSchemaVisitor(SchemaVisitor):
    """ Ensure internal representation of types match the ones in the
    schema's top level type map.

    This is useful after modifying a schema inline or using a
    :class:`SchemaVisitor` instance where a type may have swapped out but not
    all references (e.g. arguments, fields, union, etc.) were. """

    def __init__(self, schema: Schema):
        self._schema = schema

    def __call__(self) -> Schema:
        return self.visit_schema(self._schema)

    def _healed(self, original: GraphQLType) -> GraphQLType:
        if isinstance(original, NonNullType):
            return NonNullType(self._healed(original.type))
        elif isinstance(original, ListType):
            return ListType(self._healed(original.type))
        else:
            return self._schema.get_type(
                cast(NamedType, original).name, cast(NamedType, original)
            )

    def visit_schema(self, schema: Schema) -> Schema:
        return super().visit_schema(schema)

    def visit_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        updated = super().visit_object(object_type)
        if updated is not None:
            updated.interfaces = [
                cast(InterfaceType, self._healed(i)) for i in updated.interfaces
            ]
        return updated

    def visit_field(self, field: Field) -> Optional[Field]:
        updated = super().visit_field(field)
        if updated is not None:
            updated.type = self._healed(updated.type)
        return updated

    def visit_argument(self, argument: Argument) -> Optional[Argument]:
        updated = super().visit_argument(argument)
        if updated is not None:
            updated.type = self._healed(updated.type)
        return updated

    def visit_union(self, union: UnionType) -> Optional[UnionType]:
        updated = super().visit_union(union)
        if updated is not None:
            updated.types = [
                cast(ObjectType, self._healed(i)) for i in updated.types
            ]
        return updated

    def visit_input_field(self, field: InputField) -> Optional[InputField]:
        updated = super().visit_input_field(field)
        if updated is not None:
            updated.type = self._healed(updated.type)
        return updated
