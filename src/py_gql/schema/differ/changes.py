# -*- coding: utf-8 -*-

from enum import IntEnum
from typing import Any, Type, Union

from .. import (
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
    UnionType,
)


class SchemaChangeSeverity(IntEnum):
    """
    Severity level of a schema change.
    """

    #: Change should be safe for all clients.
    COMPATIBLE = 0
    #: Change could break some clients or create silent issues depending on
    #: which part of the schema they use.
    DANGEROUS = 1
    #: Change will break most clients.
    BREAKING = 2


# TODO: Add docstring describing the reasoning behind every change on each
# SchemaChange subclass.


class SchemaChange:
    severity = NotImplemented  # type: SchemaChangeSeverity
    format_str = NotImplemented  # type: str

    @property
    def message(self) -> str:
        return self.format_str.format(self=self)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, type(self)) and str(self) == str(other)


class TypeChangedKind(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "{self.type_name} changed from "
        "{self.old_kind_name} type to {self.new_kind_name} type."
    )

    def __init__(
        self,
        type_name: str,
        old_kind: Type[NamedType],
        new_kind: Type[NamedType],
    ):
        self.type_name = type_name
        self.old_kind = old_kind
        self.new_kind = new_kind
        self.old_kind_name = old_kind.__name__[:-4]
        self.new_kind_name = new_kind.__name__[:-4]


class TypeRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = "Type {self.type_name} was removed."

    def __init__(self, type_name: str):
        self.type_name = type_name


class TypeAdded(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = "Type {self.type_name} was added."

    def __init__(self, type_name: str):
        self.type_name = type_name


class TypeRemovedFromUnion(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "{self.type_name} was removed from union type {self.union.name}."
    )

    def __init__(self, type_name: str, union: UnionType):
        self.type_name = type_name
        self.union = union


class TypeAddedToUnion(SchemaChange):
    severity = SchemaChangeSeverity.DANGEROUS
    format_str = "{self.type_name} was added to union type {self.union.name}."

    def __init__(self, type_name: str, union: UnionType):
        self.type_name = type_name
        self.union = union


class TypeRemovedFromInterface(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = "{self.type.name} no longer implements {self.interface.name}."

    def __init__(self, interface: InterfaceType, object_type: ObjectType):
        self.interface = interface
        self.type = object_type


class TypeAddedToInterface(SchemaChange):
    severity = SchemaChangeSeverity.DANGEROUS
    format_str = "{self.type.name} now implements {self.interface.name}."

    def __init__(self, interface: InterfaceType, object_type: ObjectType):
        self.interface = interface
        self.type = object_type


class EnumValueRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = "{self.value.name} was removed from enum {self.enum.name}."

    def __init__(self, enum: EnumType, value: EnumValue):
        self.enum = enum
        self.value = value


class EnumValueAdded(SchemaChange):
    severity = SchemaChangeSeverity.DANGEROUS
    format_str = "{self.value.name} was added to enum {self.enum.name}."

    def __init__(self, enum: EnumType, value: EnumValue):
        self.enum = enum
        self.value = value


class EnumValueDeprecated(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "{self.old_value.name} from enum {self.enum.name} was deprecated."
    )

    def __init__(
        self, enum: EnumType, old_value: EnumValue, new_value: EnumValue
    ):
        self.enum = enum
        self.old_value = old_value
        self.new_value = new_value


class EnumValueDeprecationRemoved(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "{self.old_value.name} from enum {self.enum.name} "
        "is no longer deprecated."
    )

    def __init__(
        self, enum: EnumType, old_value: EnumValue, new_value: EnumValue
    ):
        self.enum = enum
        self.old_value = old_value
        self.new_value = new_value


class EnumValueDeprecationReasonChanged(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "{self.old_value.name} from enum {self.enum.name} "
        "has changed deprecation reason."
    )

    def __init__(
        self, enum: EnumType, old_value: EnumValue, new_value: EnumValue
    ):
        self.enum = enum
        self.old_value = old_value
        self.new_value = new_value


class DirectiveRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = "Directive {self.directive.name} was removed."

    def __init__(self, directive: Directive):
        self.directive = directive


class DirectiveAdded(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = "Directive {self.directive.name} was added."

    def __init__(self, directive: Directive):
        self.directive = directive


class DirectiveLocationRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Location {self.location} was removed from directive "
        "{self.directive.name}."
    )

    def __init__(self, directive: Directive, location: str):
        self.directive = directive
        self.location = location


class DirectiveLocationAdded(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "Location {self.location} was added to directive "
        "{self.directive.name}."
    )

    def __init__(self, directive: Directive, location: str):
        self.directive = directive
        self.location = location


class DirectiveArgumentRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Argument {self.argument.name} was removed from directive "
        "{self.directive.name}."
    )

    def __init__(self, directive: Directive, argument: Argument):
        self.directive = directive
        self.argument = argument


class DirectiveArgumentAdded(SchemaChange):
    format_str = (
        "{self.required_str} argument {self.argument.name} was added to "
        "directive {self.directive.name}."
    )

    def __init__(self, directive: Directive, argument: Argument):
        self.directive = directive
        self.argument = argument
        self.required_str = "Required" if argument.required else "Optional"
        self.severity = (
            SchemaChangeSeverity.BREAKING
            if argument.required
            else SchemaChangeSeverity.COMPATIBLE
        )


class DirectiveArgumentDefaultValueChange(SchemaChange):
    severity = SchemaChangeSeverity.DANGEROUS
    format_str = (
        "Argument {self.old_argument.name} of directive "
        "{self.directive.name} has changed default value."
    )

    def __init__(
        self,
        directive: Directive,
        old_argument: Argument,
        new_argument: Argument,
    ):
        self.directive = directive
        self.old_argument = old_argument
        self.new_argument = new_argument


class DirectiveArgumentChangedType(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Argument {self.old_argument.name} of directive {self.directive.name} "
        "has changed type from {self.old_argument.type} to {self.new_argument.type}."
    )

    def __init__(
        self,
        directive: Directive,
        old_argument: Argument,
        new_argument: Argument,
    ):
        self.directive = directive
        self.old_argument = old_argument
        self.new_argument = new_argument


class FieldArgumentRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Argument {self.argument.name} was removed from field "
        "{self.field.name} of {self.context_str} {self.type.name}."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        field: Field,
        argument: Argument,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.field = field
        self.argument = argument


class FieldArgumentAdded(SchemaChange):
    format_str = (
        "{self.required_str} argument {self.argument.name} was added to field "
        "{self.field.name} of {self.context_str} {self.type.name}."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        field: Field,
        argument: Argument,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.field = field
        self.argument = argument
        self.required_str = "Required" if argument.required else "Optional"
        self.severity = (
            SchemaChangeSeverity.BREAKING
            if argument.required
            else SchemaChangeSeverity.COMPATIBLE
        )


class FieldArgumentDefaultValueChange(SchemaChange):
    severity = SchemaChangeSeverity.DANGEROUS
    format_str = (
        "Argument {self.old_argument.name} of field "
        "{self.field.name} of {self.context_str} {self.type.name} "
        "has changed default value."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        field: Field,
        old_argument: Argument,
        new_argument: Argument,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.field = field
        self.old_argument = old_argument
        self.new_argument = new_argument


class FieldArgumentChangedType(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Argument {self.old_argument.name} of field "
        "{self.field.name} of {self.context_str} {self.type.name} "
        "has changed type from {self.old_argument.type} "
        "to {self.new_argument.type}."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        field: Field,
        old_argument: Argument,
        new_argument: Argument,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.field = field
        self.old_argument = old_argument
        self.new_argument = new_argument


class FieldChangedType(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Field {self.old_field.name} of {self.context_str} {self.type.name} has "
        "changed type from {self.old_field.type} to {self.new_field.type}."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        old_field: Field,
        new_field: Field,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.old_field = old_field
        self.new_field = new_field


class FieldRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Field {self.field.name} was removed "
        "from {self.context_str} {self.type.name}."
    )

    def __init__(
        self, parent_type: Union[ObjectType, InterfaceType], field: Field
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.field = field


class FieldAdded(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "Field {self.field.name} was added to "
        "{self.context_str} {self.type.name}."
    )

    def __init__(
        self, parent_type: Union[ObjectType, InterfaceType], field: Field
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.field = field


class FieldDeprecated(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "Field {self.old_field.name} of {self.context_str} {self.type.name} "
        "was deprecated."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        old_field: Field,
        new_field: Field,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.old_field = old_field
        self.new_field = new_field


class FieldDeprecationRemoved(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "Field {self.old_field.name} of {self.context_str} {self.type.name} "
        "is no longer deprecated."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        old_field: Field,
        new_field: Field,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.old_field = old_field
        self.new_field = new_field


class FieldDeprecationReasonChanged(SchemaChange):
    severity = SchemaChangeSeverity.COMPATIBLE
    format_str = (
        "Field {self.old_field.name} of {self.context_str} {self.type.name} has "
        "changed deprecation reason."
    )

    def __init__(
        self,
        parent_type: Union[ObjectType, InterfaceType],
        old_field: Field,
        new_field: Field,
    ):
        self.type = parent_type
        self.context_str = (
            "type" if isinstance(parent_type, ObjectType) else "interface"
        )
        self.old_field = old_field
        self.new_field = new_field


class InputFieldRemoved(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Input field {self.field.name} was removed from {self.type.name}."
    )

    def __init__(self, input_type: InputObjectType, field: InputField):
        self.type = input_type
        self.field = field


class InputFieldAdded(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "{self.required_str} input field {self.field.name} was added "
        "to {self.type.name}."
    )

    def __init__(self, input_type: InputObjectType, field: InputField):
        self.type = input_type
        self.field = field
        self.required_str = "Required" if field.required else "Optional"
        self.severity = (
            SchemaChangeSeverity.BREAKING
            if field.required
            else SchemaChangeSeverity.COMPATIBLE
        )


class InputFieldDefaultValueChange(SchemaChange):
    severity = SchemaChangeSeverity.DANGEROUS
    format_str = (
        "Input field {self.old_field.name} of {self.type.name} "
        "has changed default value."
    )

    def __init__(
        self,
        input_type: InputObjectType,
        old_field: InputField,
        new_field: InputField,
    ):
        self.type = input_type
        self.old_field = old_field
        self.new_field = new_field


class InputFieldChangedType(SchemaChange):
    severity = SchemaChangeSeverity.BREAKING
    format_str = (
        "Input field {self.old_field.name} of {self.type.name} "
        "has changed type from {self.old_field.type} to {self.new_field.type}."
    )

    def __init__(
        self,
        input_type: InputObjectType,
        old_field: InputField,
        new_field: InputField,
    ):
        self.type = input_type
        self.old_field = old_field
        self.new_field = new_field
