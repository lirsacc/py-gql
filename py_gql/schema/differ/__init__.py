# -*- coding: utf-8 -*-
"""
Utilities to compare 2 GraphQL schema for incompatibilities.
"""

import itertools
from typing import Dict, Iterator, Optional, Tuple, Type, TypeVar, Union

from .. import (
    SPECIFIED_DIRECTIVES,
    Directive,
    EnumType,
    Field,
    GraphQLType,
    InputObjectType,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    Schema,
    UnionType,
    is_introspection_type,
)
from .changes import (
    DirectiveAdded,
    DirectiveArgumentAdded,
    DirectiveArgumentChangedType,
    DirectiveArgumentDefaultValueChange,
    DirectiveArgumentRemoved,
    DirectiveLocationAdded,
    DirectiveLocationRemoved,
    DirectiveRemoved,
    EnumValueAdded,
    EnumValueDeprecated,
    EnumValueDeprecationReasonChanged,
    EnumValueDeprecationRemoved,
    EnumValueRemoved,
    FieldAdded,
    FieldArgumentAdded,
    FieldArgumentChangedType,
    FieldArgumentDefaultValueChange,
    FieldArgumentRemoved,
    FieldChangedType,
    FieldDeprecated,
    FieldDeprecationReasonChanged,
    FieldDeprecationRemoved,
    FieldRemoved,
    InputFieldAdded,
    InputFieldChangedType,
    InputFieldDefaultValueChange,
    InputFieldRemoved,
    SchemaChange,
    SchemaChangeSeverity,
    TypeAdded,
    TypeAddedToInterface,
    TypeAddedToUnion,
    TypeChangedKind,
    TypeRemoved,
    TypeRemovedFromInterface,
    TypeRemovedFromUnion,
)

TGraphQLType = TypeVar("TGraphQLType", bound=GraphQLType)


__all__ = (
    "diff_schema",
    "SchemaChange",
    "SchemaChangeSeverity",
    "DirectiveAdded",
    "DirectiveArgumentAdded",
    "DirectiveArgumentChangedType",
    "DirectiveArgumentDefaultValueChange",
    "DirectiveArgumentRemoved",
    "DirectiveLocationAdded",
    "DirectiveLocationRemoved",
    "DirectiveRemoved",
    "EnumValueAdded",
    "EnumValueDeprecated",
    "EnumValueDeprecationReasonChanged",
    "EnumValueDeprecationRemoved",
    "EnumValueRemoved",
    "FieldAdded",
    "FieldArgumentAdded",
    "FieldArgumentChangedType",
    "FieldArgumentDefaultValueChange",
    "FieldArgumentRemoved",
    "FieldChangedType",
    "FieldDeprecated",
    "FieldDeprecationReasonChanged",
    "FieldDeprecationRemoved",
    "FieldRemoved",
    "InputFieldAdded",
    "InputFieldChangedType",
    "InputFieldDefaultValueChange",
    "InputFieldRemoved",
    "TypeAdded",
    "TypeAddedToInterface",
    "TypeAddedToUnion",
    "TypeChangedKind",
    "TypeRemoved",
    "TypeRemovedFromInterface",
    "TypeRemovedFromUnion",
)


def _iterate_matching_pairs(
    old_schema: Schema, new_schema: Schema, cls: Type[TGraphQLType]
) -> Iterator[Tuple[TGraphQLType, TGraphQLType]]:
    old_types = {
        n: t for n, t in old_schema.types.items() if isinstance(t, cls)
    }  # type: Dict[str, TGraphQLType]
    new_types = {
        n: t for n, t in new_schema.types.items() if isinstance(t, cls)
    }  # type: Dict[str, TGraphQLType]

    for name, old_type in old_types.items():
        if is_introspection_type(old_type):
            continue

        try:
            yield old_type, new_types[name]
        except KeyError:
            pass


def diff_schema(
    old_schema: Schema,
    new_schema: Schema,
    min_severity: Optional[SchemaChangeSeverity] = None,
) -> Iterator[SchemaChange]:
    """
    Iterate over all changes that can be statically found between `old_schema`
    and `new_schema`.

    Some ``BREAKING`` and ``DANGEROUS`` changes could be safe depending on the
    actual queries made by clients of your schema. However it is not possible
    to detect this  without looking at the queries being run against the schema
    so this classification errs on the side of safety.

    Some compatible type changes are ignored given that they should not lead to
    any change in client behaviour.

    Args:
        old_schema: Source schema
        new_schema: Updated schema
        min_severity: Set this to filter for changes of a given severity
    """
    old_schema.validate()
    new_schema.validate()

    diffs = [
        _find_removed_types(old_schema, new_schema),
        _find_added_types(old_schema, new_schema),
        _diff_directives(old_schema, new_schema),
        _find_changed_types(old_schema, new_schema),
        _diff_union_types(old_schema, new_schema),
        _diff_enum_types(old_schema, new_schema),
        _diff_object_types(old_schema, new_schema),
        _diff_interface_types(old_schema, new_schema),
        _diff_input_types(old_schema, new_schema),
    ]

    for change in itertools.chain(*diffs):
        if min_severity is None or change.severity >= min_severity:
            yield change


def _find_removed_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for name in old.types.keys():
        if name not in new.types:
            yield TypeRemoved(name)


def _find_added_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for name in new.types.keys():
        if name not in old.types:
            yield TypeAdded(name)


def _find_changed_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for name, old_type in old.types.items():
        try:
            new_type = new.types[name]
        except KeyError:
            pass
        else:
            if old_type.__class__ != new_type.__class__:
                yield TypeChangedKind(
                    name, old_type.__class__, new_type.__class__
                )


def _diff_union_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for old_union, new_union in _iterate_matching_pairs(old, new, UnionType):
        old_type_names = set(t.name for t in old_union.types)
        new_type_names = set(t.name for t in new_union.types)

        for t in old_type_names - new_type_names:
            yield TypeRemovedFromUnion(t, old_union)

        for t in new_type_names - old_type_names:
            yield TypeAddedToUnion(t, new_union)


def _diff_enum_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for old_enum, new_enum in _iterate_matching_pairs(old, new, EnumType):
        for old_ev in old_enum.values:
            try:
                new_ev = new_enum._values[old_ev.name]
            except KeyError:
                yield EnumValueRemoved(old_enum, old_ev)
            else:
                if old_ev.deprecated:
                    if not new_ev.deprecated:
                        yield EnumValueDeprecationRemoved(
                            old_enum, old_ev, new_ev
                        )
                    elif old_ev.deprecation_reason != new_ev.deprecation_reason:
                        yield EnumValueDeprecationReasonChanged(
                            old_enum, old_ev, new_ev
                        )
                elif new_ev.deprecated:
                    yield EnumValueDeprecated(old_enum, old_ev, new_ev)

        for new_ev in new_enum.values:
            if new_ev.name not in old_enum._values:
                yield EnumValueAdded(new_enum, new_ev)


def _diff_directives(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for name, old_directive in old.directives.items():
        if old_directive in SPECIFIED_DIRECTIVES:
            continue

        try:
            new_directive = new.directives[name]
        except KeyError:
            yield DirectiveRemoved(old_directive)
        else:
            old_locs = set(old_directive.locations)
            new_locs = set(new_directive.locations)

            for loc in old_locs - new_locs:
                yield DirectiveLocationRemoved(old_directive, loc)

            for loc in new_locs - old_locs:
                yield DirectiveLocationAdded(old_directive, loc)

            for d in _diff_directive_arguments(old_directive, new_directive):
                yield d

    for name, new_directive in new.directives.items():
        if new_directive in SPECIFIED_DIRECTIVES:
            continue

        if name not in old.directives:
            yield DirectiveAdded(new_directive)


def _diff_directive_arguments(
    old_directive: Directive, new_directive: Directive
) -> Iterator[SchemaChange]:

    old_args = old_directive.argument_map
    new_args = new_directive.argument_map

    for name, old_arg in old_args.items():
        try:
            new_arg = new_args[name]
        except KeyError:
            yield DirectiveArgumentRemoved(old_directive, old_arg)
        else:
            if not _is_safe_input_type_change(old_arg.type, new_arg.type):
                yield DirectiveArgumentChangedType(
                    old_directive, old_arg, new_arg
                )
            elif (
                (old_arg.has_default_value and not new_arg.has_default_value)
                or (not old_arg.has_default_value and new_arg.has_default_value)
                or (
                    old_arg.has_default_value
                    and old_arg.default_value != new_arg.default_value
                )
            ):
                yield DirectiveArgumentDefaultValueChange(
                    old_directive, old_arg, new_arg
                )

    for name, new_arg in new_args.items():
        if name not in old_args:
            yield DirectiveArgumentAdded(new_directive, new_arg)


def _diff_field_arguments(
    parent: Union[ObjectType, InterfaceType], old_field: Field, new_field: Field
) -> Iterator[SchemaChange]:

    old_args = old_field.argument_map
    new_args = new_field.argument_map

    for name, old_arg in old_args.items():
        try:
            new_arg = new_args[name]
        except KeyError:
            yield FieldArgumentRemoved(parent, old_field, old_arg)
        else:
            if not _is_safe_input_type_change(old_arg.type, new_arg.type):
                yield FieldArgumentChangedType(
                    parent, old_field, old_arg, new_arg
                )
            elif (
                (old_arg.has_default_value and not new_arg.has_default_value)
                or (not old_arg.has_default_value and new_arg.has_default_value)
                or (
                    old_arg.has_default_value
                    and old_arg.default_value != new_arg.default_value
                )
            ):
                yield FieldArgumentDefaultValueChange(
                    parent, old_field, old_arg, new_arg
                )

    for name, new_arg in new_args.items():
        if name not in old_args:
            yield FieldArgumentAdded(parent, new_field, new_arg)


def _is_safe_input_type_change(
    old_type: GraphQLType, new_type: GraphQLType
) -> bool:
    if isinstance(old_type, NamedType):
        return bool(
            isinstance(new_type, NamedType) and old_type.name == new_type.name
        )
    elif isinstance(old_type, ListType):
        return isinstance(new_type, ListType) and _is_safe_input_type_change(
            old_type.type, new_type.type
        )
    elif isinstance(old_type, NonNullType):
        return (
            isinstance(new_type, NonNullType)
            and _is_safe_input_type_change(old_type.type, new_type.type)
        ) or (
            not isinstance(new_type, NonNullType)
            and _is_safe_input_type_change(old_type.type, new_type)
        )
    return False


def _is_safe_output_type_change(
    old_type: GraphQLType, new_type: GraphQLType
) -> bool:
    if isinstance(old_type, NamedType):
        return (
            isinstance(new_type, NamedType) and old_type.name == new_type.name
        ) or (
            isinstance(new_type, NonNullType)
            and _is_safe_output_type_change(old_type, new_type.type)
        )
    elif isinstance(old_type, ListType):
        return (
            isinstance(new_type, ListType)
            and _is_safe_input_type_change(old_type.type, new_type.type)
        ) or (
            isinstance(new_type, NonNullType)
            and _is_safe_output_type_change(old_type, new_type.type)
        )
    elif isinstance(old_type, NonNullType):
        return isinstance(
            new_type, NonNullType
        ) and _is_safe_output_type_change(old_type.type, new_type.type)
    return False


def _diff_object_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for old_object, new_object in _iterate_matching_pairs(old, new, ObjectType):
        for field_name, old_field in old_object.field_map.items():
            try:
                new_field = new_object.field_map[field_name]
            except KeyError:
                yield FieldRemoved(old_object, old_field)
            else:
                for d in _diff_field(old_field, new_field, old_object):
                    yield d

        for new_field in new_object.field_map.values():
            if new_field.name not in old_object.field_map:
                yield FieldAdded(new_object, new_field)

        old_interfaces = {i.name: i for i in old_object.interfaces}
        new_interfaces = {i.name: i for i in new_object.interfaces}

        for iname, i in old_interfaces.items():
            if iname not in new_interfaces:
                yield TypeRemovedFromInterface(i, old_object)

        for iname, i in new_interfaces.items():
            if iname not in old_interfaces:
                yield TypeAddedToInterface(i, old_object)


def _diff_interface_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for old_interface, new_interface in _iterate_matching_pairs(
        old, new, InterfaceType
    ):
        for field_name, old_field in old_interface.field_map.items():
            try:
                new_field = new_interface.field_map[field_name]
            except KeyError:
                yield FieldRemoved(old_interface, old_field)
            else:
                for d in _diff_field(old_field, new_field, old_interface):
                    yield d

        for new_field in new_interface.field_map.values():
            if new_field.name not in old_interface.field_map:
                yield FieldAdded(new_interface, new_field)


def _diff_field(
    old: Field, new: Field, parent_type: Union[ObjectType, InterfaceType]
) -> Iterator[SchemaChange]:
    if not _is_safe_output_type_change(old.type, new.type):
        yield FieldChangedType(parent_type, old, new)

    for d in _diff_field_arguments(parent_type, old, new):
        yield d

    if old.deprecated:
        if not new.deprecated:
            yield FieldDeprecationRemoved(parent_type, old, new)
        elif old.deprecation_reason != new.deprecation_reason:
            yield FieldDeprecationReasonChanged(parent_type, old, new)
    elif new.deprecated:
        yield FieldDeprecated(parent_type, old, new)


def _diff_input_types(old: Schema, new: Schema) -> Iterator[SchemaChange]:
    for old_type, new_type in _iterate_matching_pairs(
        old, new, InputObjectType
    ):
        old_fields = old_type.field_map
        new_fields = new_type.field_map

        for name, old_field in old_fields.items():
            try:
                new_field = new_fields[name]
            except KeyError:
                yield InputFieldRemoved(old_type, old_field)
            else:
                if not _is_safe_input_type_change(
                    old_field.type, new_field.type
                ):
                    yield InputFieldChangedType(old_type, old_field, new_field)
                elif (
                    (
                        old_field.has_default_value
                        and not new_field.has_default_value
                    )
                    or (
                        not old_field.has_default_value
                        and new_field.has_default_value
                    )
                    or (
                        old_field.has_default_value
                        and old_field.default_value != new_field.default_value
                    )
                ):
                    yield InputFieldDefaultValueChange(
                        old_type, old_field, new_field
                    )

        for name, new_field in new_fields.items():
            if name not in old_fields:
                yield InputFieldAdded(new_type, new_field)
