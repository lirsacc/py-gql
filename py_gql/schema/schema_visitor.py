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


TType = TypeVar("TType", bound=type)


class SchemaVisitor(object):
    """
    Base class encoding schema traversal and modifications.

    Subclass and override the ``on_*`` methods to implement custom behaviour.

    All methods *must* return the modified value; returning ``None`` will drop
    the respective values from their context, e.g. returning ``None`` from
    :meth:`on_field` will result in the field being dropped from the parent
    :class:`py_gql.schema.ObjectType`.

    For most uses cases, do not forget to call the method from the parent class
    as it ususally encodes how child elements such as field, enum values, etc.
    are processed.
    """

    def on_schema(self, schema: Schema) -> Schema:
        """
        Process the whole schema. You **should not** override this in most cases.

        Args:
            schema: Original schema.
        """
        updated_types = {}

        for type_name, original in schema.types.items():
            if type_name.startswith("__") or original in SPECIFIED_SCALAR_TYPES:
                continue

            if isinstance(original, ObjectType):
                updated = self.on_object(
                    original
                )  # type: Optional[GraphQLType]
            elif isinstance(original, InterfaceType):
                updated = self.on_interface(original)
            elif isinstance(original, InputObjectType):
                updated = self.on_input_object(original)
            elif isinstance(original, ScalarType):
                updated = self.on_scalar(original)
            elif isinstance(original, UnionType):
                updated = self.on_union(original)
            elif isinstance(original, EnumType):
                updated = self.on_enum(original)
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

    def on_scalar(self, scalar_type: ScalarType) -> Optional[ScalarType]:
        """
        Args:
            scalar: Original type.
        """
        return scalar_type

    def on_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        """
        Args:
            object_type: Original type.
        """
        updated_fields = list(
            map_and_filter(self.on_field_definition, object_type.fields)
        )
        if updated_fields != object_type.fields:
            object_type._fields = updated_fields
        return object_type

    def on_field_definition(self, field: Field) -> Optional[Field]:
        """
        Args:
            field: Original object field.
        """
        updated_args = list(
            map_and_filter(self.on_argument_definition, field.arguments)
        )
        if updated_args != field.arguments:
            field._args = updated_args
        return field

    def on_argument_definition(self, argument: Argument) -> Optional[Argument]:
        """
        Args:
            field: Original argument.
        """
        return argument

    def on_interface(
        self, interface_type: InterfaceType
    ) -> Optional[InterfaceType]:
        """
        Args:
            interface_type: Original type.
        """
        updated_fields = list(
            map_and_filter(self.on_field_definition, interface_type.fields)
        )
        if updated_fields != interface_type.fields:
            interface_type._fields = updated_fields
        return interface_type

    def on_union(self, union_type: UnionType) -> Optional[UnionType]:
        """
        Args:
            union_type: Original type.
        """
        return union_type

    def on_enum(self, enum_type: EnumType) -> Optional[EnumType]:
        """
        Args:
            enum_type: Original type.
        """
        updated_values = list(
            map_and_filter(self.on_enum_value, enum_type.values)
        )
        if updated_values != enum_type.values:
            enum_type._set_values(updated_values)
        return enum_type

    def on_enum_value(self, enum_value: EnumValue) -> Optional[EnumValue]:
        """
        Args:
            enum_value: Original enum value.
        """
        return enum_value

    def on_input_object(
        self, input_object_type: InputObjectType
    ) -> Optional[InputObjectType]:
        """
        Args:
            input_object_type: Original type.
        """
        updated_fields = list(
            map_and_filter(
                self.on_input_field_definition, input_object_type.fields
            )
        )
        if updated_fields != input_object_type.fields:
            input_object_type._fields = updated_fields
        return input_object_type

    def on_input_field_definition(
        self, field: InputField
    ) -> Optional[InputField]:
        """
        Args:
            field: Original input object field.
        """
        return field
