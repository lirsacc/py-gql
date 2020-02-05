# -*- coding: utf-8 -*-
from typing import Optional, TypeVar

from ..._utils import map_and_filter
from ...schema import (
    SPECIFIED_SCALAR_TYPES,
    Directive,
    EnumType,
    InputField,
    InputObjectType,
    InterfaceType,
    NamedType,
    ObjectType,
    ScalarType,
    SchemaVisitor,
    UnionType,
    unwrap_type,
)
from ...schema.introspection import INTROPSPECTION_TYPES

TNamedType = TypeVar("TNamedType", bound=NamedType)


class VisibilitySchemaTransform(SchemaVisitor):
    """Remove elements from a schema.

    User should subclass this and override the various visibility hooks.

    The following elements are affected directly:

        - Named types (is_type_visible)
        - Object and interface fields (is_field_visible)
        - Directives (is_directive_visible)
        - Input type fields (is_input_field_visible)

    The following elements are affected indirectly:

        - Object fields of a type that is now hidden
        - Input fields of a type that is now hidden
        - Arguments of a type that is now hidden

    Warning:
        Mandatory input fields and arguments being removed could break
        resolvers if they were not built anticipating this (e.g. expected an
        argument as a mandatory keyword argument).

    This should not allow modifying a schema to be off-spec and as such the
    following elements (or their children) cannot be hidden:

        - The query type
        - Specified scalar types
        - Introspection types
        - Specified directives

    Users should use this transform before using the schema to make sure that
    validation, execution and introspection take the modifications into account.
    """

    def is_type_visible(self, name: str) -> bool:
        return True

    def is_directive_visible(self, name: str) -> bool:
        return True

    def is_field_visible(self, typename: str, fieldname: str) -> bool:
        return True

    def is_input_field_visible(self, typename: str, fieldname: str) -> bool:
        return True

    def _is_type_visible(self, named_type: NamedType) -> bool:
        return (
            named_type in SPECIFIED_SCALAR_TYPES
            or named_type in INTROPSPECTION_TYPES
            or self.is_type_visible(named_type.name)
        )

    def _filter_type(
        self, named_type: Optional[TNamedType]
    ) -> Optional[TNamedType]:
        if named_type is None or not self._is_type_visible(named_type):
            return None
        return named_type

    def on_scalar(self, scalar_type: ScalarType) -> Optional[ScalarType]:
        return self._filter_type(super().on_scalar(scalar_type))

    def on_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        if not self._is_type_visible(object_type):
            return None

        updated_fields = map_and_filter(
            lambda field: (
                field
                if self.is_field_visible(object_type.name, field.name)
                else None
            ),
            object_type.fields,
        )
        if updated_fields != object_type.fields:
            object_type.fields = updated_fields

        return super().on_object(object_type)

    def on_interface(
        self, interface_type: InterfaceType
    ) -> Optional[InterfaceType]:
        if not self._is_type_visible(interface_type):
            return None

        def _filter_field(field):
            return (
                field
                if self.is_field_visible(interface_type.name, field.name)
                else None
            )

        updated_fields = map_and_filter(_filter_field, interface_type.fields)
        if updated_fields != interface_type.fields:
            interface_type.fields = updated_fields

        return super().on_interface(interface_type)

    def on_union(self, union_type: UnionType) -> Optional[UnionType]:
        return self._filter_type(super().on_union(union_type))

    def on_enum(self, enum_type: EnumType) -> Optional[EnumType]:
        return self._filter_type(super().on_enum(enum_type))

    def on_input_object(
        self, input_object_type: InputObjectType
    ) -> Optional[InputObjectType]:

        updated_fields = map_and_filter(
            lambda input_field: (
                input_field
                if self.is_input_field_visible(
                    input_object_type.name, input_field.name
                )
                else None
            ),
            input_object_type.fields,
        )
        if updated_fields != input_object_type.fields:
            input_object_type.fields = updated_fields

        return self._filter_type(super().on_input_object(input_object_type))

    def on_input_field(self, field: InputField) -> Optional[InputField]:
        if self._is_type_visible(unwrap_type(field.type)):
            return super().on_input_field(field)
        return None

    def on_directive(self, directive: Directive) -> Optional[Directive]:
        if directive and not self.is_directive_visible(directive.name):
            return None
        return super().on_directive(directive)
