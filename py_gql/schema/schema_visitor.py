# -*- coding: utf-8 -*-

from typing import Optional, TypeVar

from .._utils import map_and_filter
from .directives import SPECIFIED_DIRECTIVES
from .scalars import SPECIFIED_SCALAR_TYPES
from .schema import Schema
from .types import (
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    InputField,
    InputObjectType,
    InterfaceType,
    NamedType,
    ObjectType,
    ScalarType,
    UnionType,
)

TType = TypeVar("TType", bound=type)


class SchemaVisitor(object):
    """
    Base class encoding schema traversal and modifications.

    Subclass and override the ``on_*`` methods to implement custom behaviour.

    All methods *must* return the modified value; returning ``None`` will drop
    the respective values from their context, e.g. returning ``None`` from
    :meth:`on_field` will result in the field being dropped from the parent
    :class:`py_gql.schema.ObjectType`. However, types and directives are
    **never** from the schema, even if not in use anymore.

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
        updated_types = []
        updated_directives = []

        for original_type in schema.types.values():
            if original_type.name.startswith("__"):
                continue

            if isinstance(original_type, ObjectType):
                updated = self.on_object(
                    original_type
                )  # type: Optional[NamedType]
            elif isinstance(original_type, InterfaceType):
                updated = self.on_interface(original_type)
            elif isinstance(original_type, InputObjectType):
                updated = self.on_input_object(original_type)
            elif isinstance(original_type, ScalarType):
                updated = self.on_scalar(original_type)
            elif isinstance(original_type, UnionType):
                updated = self.on_union(original_type)
            elif isinstance(original_type, EnumType):
                updated = self.on_enum(original_type)
            else:
                raise TypeError(type(original_type))

            if updated is not None and updated is not original_type:
                updated_types.append(updated)

        for original_directive in schema.directives.values():
            updated_directive = self.on_directive(original_directive)
            if (
                updated_directive is not None
                and updated_directive is not original_directive
            ):
                updated_directives.append(updated_directive)

        if not updated_types and not updated_directives:
            return schema

        schema._replace_types_and_directives(updated_types, updated_directives)

        return schema

    def on_scalar(self, scalar_type: ScalarType) -> Optional[ScalarType]:
        """
        Args:
            scalar: Original type.
        """
        if scalar_type in SPECIFIED_SCALAR_TYPES:
            return scalar_type

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
            object_type.fields = updated_fields
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
            field.arguments = updated_args
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
            interface_type.fields = updated_fields
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
            input_object_type.fields = updated_fields
        return input_object_type

    def on_input_field_definition(
        self, field: InputField
    ) -> Optional[InputField]:
        """
        Args:
            field: Original input object field.
        """
        return field

    def on_directive(self, directive: Directive) -> Directive:
        """
        Note:
            This does not correspond to a directive location but is necessary
            to completely cover schema traversal.

        Args:
            directive: Original directive
        """
        if directive in SPECIFIED_DIRECTIVES:
            return directive

        updated_args = list(
            map_and_filter(self.on_argument_definition, directive.arguments)
        )
        if updated_args != directive.arguments:
            directive.arguments = updated_args
        return directive
