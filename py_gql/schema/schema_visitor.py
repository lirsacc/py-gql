# -*- coding: utf-8 -*-

from typing import Dict, Optional, TypeVar

from .._utils import deprecated, map_and_filter
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
    Do not forget to call the superclass methods as it ususally  encodes how
    child elements such as field, enum values, etc. are processed.

    All methods *must* return the modified value; returning ``None`` will drop
    the respective values from their context, e.g. returning ``None`` from
    :meth:`on_field` will result in the field being dropped from the parent
    :class:`py_gql.schema.ObjectType`.

    Specified types (scalars, introspection) and directives are ignored.
    """

    def on_schema(self, schema: Schema) -> Schema:
        """
        Process the whole schema. Consumers will most likely not need to override
        this in most cases.

        """
        updated_types = {}  # type: Dict[str, Optional[NamedType]]
        updated_directives = {}  # type: Dict[str, Optional[Directive]]

        for original_type in schema.types.values():
            if (
                original_type.name.startswith("__")
                or original_type in SPECIFIED_SCALAR_TYPES
            ):
                continue

            updated = None  # type: Optional[NamedType]

            if isinstance(original_type, ObjectType):
                updated = self.on_object(original_type)
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

            if updated is not original_type:
                updated_types[original_type.name] = updated

        for original_directive in schema.directives.values():
            if original_directive in SPECIFIED_DIRECTIVES:
                continue

            updated_directive = self.on_directive(original_directive)

            if updated_directive is not original_directive:
                updated_directives[original_directive.name] = updated_directive

        schema._replace_types_and_directives(updated_types, updated_directives)
        return schema

    def on_scalar(self, scalar_type: ScalarType) -> Optional[ScalarType]:
        return scalar_type

    def on_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        updated_fields = map_and_filter(self.on_field, object_type.fields)
        if updated_fields != object_type.fields:
            return ObjectType(
                object_type.name,
                updated_fields,
                interfaces=object_type.interfaces,
                default_resolver=object_type.default_resolver,
                description=object_type.description,
                nodes=object_type.nodes,
            )
        return object_type

    def on_field(self, field: Field) -> Optional[Field]:
        updated_args = map_and_filter(self.on_argument, field.arguments)
        if updated_args != field.arguments:
            return Field(
                field.name,
                field.type,
                args=updated_args,
                description=field.description,
                deprecation_reason=field.deprecation_reason,
                resolver=field.resolver,
                subscription_resolver=field.subscription_resolver,
                node=field.node,
                python_name=field.python_name,
            )
        return field

    def on_argument(self, argument: Argument) -> Optional[Argument]:
        return argument

    def on_interface(
        self, interface_type: InterfaceType
    ) -> Optional[InterfaceType]:
        updated_fields = map_and_filter(self.on_field, interface_type.fields)
        if updated_fields != interface_type.fields:
            return InterfaceType(
                interface_type.name,
                updated_fields,
                resolve_type=interface_type.resolve_type,
                description=interface_type.description,
                nodes=interface_type.nodes,
            )
        return interface_type

    def on_union(self, union_type: UnionType) -> Optional[UnionType]:
        return union_type

    def on_enum(self, enum_type: EnumType) -> Optional[EnumType]:
        updated_values = map_and_filter(self.on_enum_value, enum_type.values)
        if updated_values != enum_type.values:
            return EnumType(
                enum_type.name,
                values=updated_values,
                description=enum_type.description,
                nodes=enum_type.nodes,
            )
        return enum_type

    def on_enum_value(self, enum_value: EnumValue) -> Optional[EnumValue]:
        return enum_value

    def on_input_object(
        self, input_object_type: InputObjectType
    ) -> Optional[InputObjectType]:
        updated_fields = map_and_filter(
            self.on_input_field, input_object_type.fields
        )
        if updated_fields != input_object_type.fields:
            return InputObjectType(
                input_object_type.name,
                updated_fields,
                description=input_object_type.description,
                nodes=input_object_type.nodes,
            )
        return input_object_type

    def on_input_field(self, field: InputField) -> Optional[InputField]:
        return field

    def on_directive(self, directive: Directive) -> Optional[Directive]:
        updated_args = map_and_filter(self.on_argument, directive.arguments)
        if updated_args != directive.arguments:
            return Directive(
                directive.name,
                directive.locations,
                args=updated_args,
                description=directive.description,
                node=directive.node,
            )
        return directive

    on_field_definition = deprecated(
        "This method has been deprecated, use on_field instead."
    )(on_field)

    on_input_field_definition = deprecated(
        "This method has been deprecated, use on_input_field instead."
    )(on_input_field)

    on_argument_definition = deprecated(
        "This method has been deprecated, use on_argument instead."
    )(on_argument)
