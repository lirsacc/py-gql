# -*- coding: utf-8 -*-

from typing import Optional, TypeVar, cast

from .._utils import map_and_filter
from .directives import SPECIFIED_DIRECTIVES
from .scalars import SPECIFIED_SCALAR_TYPES
from .schema import Schema
from .types import (
    Argument,
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

_SPECIFIED_DIRECTIVE_NAMES = frozenset(d.name for d in SPECIFIED_DIRECTIVES)


AT = TypeVar("AT", bound=type)


class SchemaVisitor(object):
    """ Base class to encode schema traversal and inline modifications.

    Subclass and override the ``visit_*`` methods to implement custom behaviour.
    All visitor methods *must* return the modified value; returning ``None``
    will drop the respective values from their context, e.g. returning ``None``
    from :meth:`visit_field` will result in the field being dropped from the
    parent :class:`py_gql.schema.ObjectType`.
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

        def _get_or(t: Optional[ObjectType]) -> Optional[ObjectType]:
            return cast(ObjectType, updated_types.get(t.name, t)) if t else None

        schema.query_type = _get_or(schema.query_type)
        schema.mutation_type = _get_or(schema.mutation_type)
        schema.subscription_type = _get_or(schema.subscription_type)

        schema._rebuild_caches()

        return schema

    def visit_scalar(self, scalar: ScalarType[AT]) -> Optional[ScalarType[AT]]:
        return scalar

    def visit_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        updated_fields = list(
            map_and_filter(self.visit_field, object_type.fields)
        )
        if updated_fields != object_type.fields:
            object_type._fields = updated_fields
        return object_type

    def visit_field(self, field: Field) -> Optional[Field]:
        updated_args = list(
            map_and_filter(self.visit_argument, field.arguments)
        )
        if updated_args != field.arguments:
            field._args = updated_args
        return field

    def visit_argument(self, argument: Argument) -> Optional[Argument]:
        return argument

    def visit_interface(
        self, interface: InterfaceType
    ) -> Optional[InterfaceType]:
        updated_fields = list(
            map_and_filter(self.visit_field, interface.fields)
        )
        if updated_fields != interface.fields:
            interface._fields = updated_fields
        return interface

    def visit_union(self, union: UnionType) -> Optional[UnionType]:
        return union

    def visit_enum(self, enum: EnumType) -> Optional[EnumType]:
        updated_values = list(
            map_and_filter(self.visit_enum_value, enum.values)
        )
        if updated_values != enum.values:
            enum._set_values(updated_values)
        return enum

    def visit_enum_value(self, enum_value: EnumValue) -> Optional[EnumValue]:
        return enum_value

    def visit_input_object(
        self, input_object: InputObjectType
    ) -> Optional[InputObjectType]:
        updated_fields = list(
            map_and_filter(self.visit_input_field, input_object.fields)
        )
        if updated_fields != input_object.fields:
            input_object._fields = updated_fields
        return input_object

    def visit_input_field(self, field: InputField) -> Optional[InputField]:
        return field
