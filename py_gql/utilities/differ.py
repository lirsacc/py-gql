# -*- coding: utf-8 -*-

import enum
import itertools
from typing import Any, Dict, Iterator, Mapping, Optional, Tuple, Type, TypeVar

from ..schema import (
    Argument,
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
    Schema,
    UnionType,
)

__all__ = ("SchemaChange", "SchemaChangeSeverity", "diff_schema")


class SchemaChangeSeverity(enum.IntEnum):
    """
    Severity level of a schema change.
    """

    COMPATIBLE = 0
    DANGEROUS = 1
    BREAKING = 2


class SchemaChange(enum.Enum):
    """
    Representation of a schema change.
    """

    def __init__(
        self, name: str, severity: SchemaChangeSeverity, format_str: str
    ):
        self._name = name
        self.severity = severity
        self.format_str = format_str

    def __str__(self):
        return self._name

    def __repr__(self):
        return "<Delta {}>".format(self._name)

    TYPE_CHANGED_KIND = (
        "TYPE_CHANGED_KIND",
        SchemaChangeSeverity.BREAKING,
        "{} changed from an {} type to a {} type.",
    )

    TYPE_REMOVED = (
        "TYPE_REMOVED",
        SchemaChangeSeverity.BREAKING,
        "Type {} was removed.",
    )
    TYPE_ADDED = (
        "TYPE_ADDED",
        SchemaChangeSeverity.COMPATIBLE,
        "Type {} was added.",
    )

    TYPE_REMOVED_FROM_UNION = (
        "TYPE_REMOVED_FROM_UNION",
        SchemaChangeSeverity.BREAKING,
        "{} was removed from union type {}.",
    )
    TYPE_ADDED_TO_UNION = (
        "TYPE_ADDED_TO_UNION",
        SchemaChangeSeverity.DANGEROUS,
        "{} was added to union type {}.",
    )

    TYPE_REMOVED_FROM_INTERFACE = (
        "TYPE_REMOVED_FROM_INTERFACE",
        SchemaChangeSeverity.BREAKING,
        "{} no longer implements {}.",
    )
    TYPE_ADDED_TO_INTERFACE = (
        "TYPE_ADDED_TO_INTERFACE",
        SchemaChangeSeverity.DANGEROUS,
        "{} now implements {}.",
    )

    VALUE_REMOVED_FROM_ENUM = (
        "VALUE_REMOVED_FROM_ENUM",
        SchemaChangeSeverity.BREAKING,
        "{} was removed from enum type {}.",
    )
    VALUE_ADDED_TO_ENUM = (
        "VALUE_ADDED_TO_ENUM",
        SchemaChangeSeverity.DANGEROUS,
        "{} was added to enum type {}.",
    )
    ENUM_VALUE_DEPRECATED = (
        "ENUM_VALUE_DEPRECATED",
        SchemaChangeSeverity.COMPATIBLE,
        "{} from enum type {} was deprecated.",
    )
    ENUM_VALUE_DEPRECATION_REMOVED = (
        "ENUM_VALUE_DEPRECATION_REMOVED",
        SchemaChangeSeverity.COMPATIBLE,
        "{} from enum type {} is no longer deprecated.",
    )
    ENUM_VALUE_DEPRECATION_REASON_CHANGE = (
        "ENUM_VALUE_DEPRECATION_REASON_CHANGE",
        SchemaChangeSeverity.COMPATIBLE,
        "{} from enum type {} has changed deprecation reason.",
    )

    DIRECTIVE_REMOVED = (
        "DIRECTIVE_REMOVED",
        SchemaChangeSeverity.BREAKING,
        "Directive {} was removed.",
    )
    DIRECTIVE_ADDED = (
        "DIRECTIVE_ADDED",
        SchemaChangeSeverity.COMPATIBLE,
        "Directive {} was added.",
    )
    DIRECTIVE_LOCATION_REMOVED = (
        "DIRECTIVE_LOCATION_REMOVED",
        SchemaChangeSeverity.BREAKING,
        "Location {} was removed from directive {}.",
    )
    DIRECTIVE_LOCATION_ADDED = (
        "DIRECTIVE_LOCATION_ADDED",
        SchemaChangeSeverity.COMPATIBLE,
        "Location {} was added to directive {}.",
    )

    ARG_REMOVED = (
        "ARG_REMOVED",
        SchemaChangeSeverity.BREAKING,
        "Argument {} was removed from {}.",
    )
    REQUIRED_ARG_ADDED = (
        "REQUIRED_ARG_ADDED",
        SchemaChangeSeverity.BREAKING,
        "Required argument {} was added to {}.",
    )
    OPTIONAL_ARG_ADDED = (
        "OPTIONAL_ARG_ADDED",
        SchemaChangeSeverity.COMPATIBLE,
        "Optional argument {} was added to {}.",
    )
    ARG_DEFAULT_VALUE_CHANGE = (
        "ARG_DEFAULT_VALUE_CHANGE",
        SchemaChangeSeverity.DANGEROUS,
        "Argument {} of {} has changed default value.",
    )
    ARG_CHANGED_TYPE = (
        "ARG_CHANGED_TYPE",
        SchemaChangeSeverity.BREAKING,
        "Argument {} of {} has changed type from {} to {}.",
    )

    FIELD_CHANGED_TYPE = (
        "FIELD_CHANGED_TYPE",
        SchemaChangeSeverity.BREAKING,
        "Field {} of {} has changed type from {} to {}.",
    )
    FIELD_REMOVED = (
        "FIELD_REMOVED",
        SchemaChangeSeverity.BREAKING,
        "Field {} was removed from {}.",
    )
    FIELD_ADDED = (
        "FIELD_ADDED",
        SchemaChangeSeverity.COMPATIBLE,
        "Field {} was added to {}.",
    )

    FIELD_DEPRECATED = (
        "FIELD_DEPRECATED",
        SchemaChangeSeverity.COMPATIBLE,
        "Field {} of {} was deprecated.",
    )
    FIELD_DEPRECATION_REMOVED = (
        "FIELD_DEPRECATION_REMOVED",
        SchemaChangeSeverity.COMPATIBLE,
        "Field {} of {} is no longer deprecated.",
    )
    FIELD_DEPRECATION_REASON_CHANGED = (
        "FIELD_DEPRECATION_REASON_CHANGED",
        SchemaChangeSeverity.COMPATIBLE,
        "Field {} of {} has changed deprecation reason.",
    )

    INPUT_FIELD_REMOVED = (
        "INPUT_FIELD_REMOVED",
        SchemaChangeSeverity.BREAKING,
        "Input field {} was removed from {}.",
    )
    REQUIRED_INPUT_FIELD_ADDED = (
        "REQUIRED_INPUT_FIELD_ADDED",
        SchemaChangeSeverity.BREAKING,
        "Required input field {} was added to {}.",
    )
    OPTIONAL_INPUT_FIELD_ADDED = (
        "OPTIONAL_INPUT_FIELD_ADDED",
        SchemaChangeSeverity.COMPATIBLE,
        "Optional argument {} was added to {}.",
    )
    INPUT_FIELD_DEFAULT_VALUE_CHANGE = (
        "INPUT_FIELD_DEFAULT_VALUE_CHANGE",
        SchemaChangeSeverity.DANGEROUS,
        "Input field {} of {} has changed default value.",
    )
    INPUT_FIELD_CHANGED_TYPE = (
        "INPUT_FIELD_CHANGED_TYPE",
        SchemaChangeSeverity.BREAKING,
        "Input field {} of {} has changed type from {} to {}.",
    )


DiffParams = Tuple[SchemaChange, Tuple[Any, ...]]
Diff = Tuple[SchemaChange, str]
TGraphQLType = TypeVar("TGraphQLType", bound=GraphQLType)


def _of_type(
    schema: Schema, cls: Type[TGraphQLType]
) -> Dict[str, TGraphQLType]:
    return {n: t for n, t in schema.types.items() if isinstance(t, cls)}


def _old_and_new(
    old_schema: Schema, new_schema: Schema, cls: Type[TGraphQLType]
) -> Iterator[Tuple[str, TGraphQLType, TGraphQLType]]:
    old_types = _of_type(old_schema, cls)
    new_types = _of_type(new_schema, cls)

    for name, old_type in old_types.items():
        try:
            yield name, old_type, new_types[name]
        except KeyError:
            pass


def diff_schema(
    old_schema: Schema,
    new_schema: Schema,
    min_severity: Optional[SchemaChangeSeverity] = None,
) -> Iterator[Diff]:
    """
    List all differences that can be statically found between `old_schema` and
    `new_schema`. The differences are classified by severity as:

    - `SchemaChangeSeverity.BREAKING`: will break most clients
    - `SchemaChangeSeverity.DANGEROUS`: could break some clients depending on usage
    - `SchemaChangeSeverity.COMPATIBLE`: safe change

    Some BREAKING and DANGEROUS changes could be safe depending on the actual
    queries made by clients of your schema. However it is not possible to detect
    this  without looking at the usage of the schema so this classification
    should err on the side of safety.

    Some compatible type changes are ignored given that they should not lead to
    any change in client behaviour.

    Args:
        old_schema: Source schema
        new_schema: Updated schema
        level: Set this to filter for changes of a given severity

    Yields:
        (change, change description)
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

    for change, format_args in itertools.chain(*diffs):
        if min_severity is None or change.severity >= min_severity:
            yield change, change.format_str.format(*format_args)


def _find_removed_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name in old.types.keys():
        if name not in new.types:
            yield SchemaChange.TYPE_REMOVED, (name,)


def _find_added_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name in new.types.keys():
        if name not in old.types:
            yield SchemaChange.TYPE_ADDED, (name,)


def _find_changed_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_type in old.types.items():
        try:
            new_type = new.types[name]
        except KeyError:
            pass
        else:
            if old_type.__class__ != new_type.__class__:
                yield (
                    SchemaChange.TYPE_CHANGED_KIND,
                    (
                        name,
                        old_type.__class__.__name__[:-4],
                        new_type.__class__.__name__[:-4],
                    ),
                )


def _diff_union_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_union, new_union in _old_and_new(old, new, UnionType):
        old_type_names = set(t.name for t in old_union.types)
        new_type_names = set(t.name for t in new_union.types)

        for t in old_type_names - new_type_names:
            yield SchemaChange.TYPE_REMOVED_FROM_UNION, (t, name)

        for t in new_type_names - old_type_names:
            yield SchemaChange.TYPE_ADDED_TO_UNION, (t, name)


def _diff_enum_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_enum, new_enum in _old_and_new(old, new, EnumType):
        for ev in old_enum.values:
            try:
                new_ev = new_enum._values[ev.name]
            except KeyError:
                yield SchemaChange.VALUE_REMOVED_FROM_ENUM, (ev.name, name)
            else:
                for d in _diff_enum_values(ev, new_ev, name):
                    yield d

        for new_ev in new_enum.values:
            if new_ev.name not in old_enum._values:
                yield SchemaChange.VALUE_ADDED_TO_ENUM, (new_ev.name, name)


def _diff_enum_values(
    old: EnumValue, new: EnumValue, parent: str
) -> Iterator[DiffParams]:
    if old.deprecated:
        if not new.deprecated:
            yield (
                SchemaChange.ENUM_VALUE_DEPRECATION_REMOVED,
                (old.name, parent),
            )
        elif old.deprecation_reason != new.deprecation_reason:
            yield (
                SchemaChange.ENUM_VALUE_DEPRECATION_REASON_CHANGE,
                (old.name, parent),
            )
    elif new.deprecated:
        yield SchemaChange.ENUM_VALUE_DEPRECATED, (old.name, parent)


def _diff_directives(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_directive in old.directives.items():
        try:
            new_directive = new.directives[name]
        except KeyError:
            yield SchemaChange.DIRECTIVE_REMOVED, (name,)
        else:
            old_locs = set(old_directive.locations)
            new_locs = set(new_directive.locations)

            for loc in old_locs - new_locs:
                yield SchemaChange.DIRECTIVE_LOCATION_REMOVED, (loc, name)

            for loc in new_locs - old_locs:
                yield SchemaChange.DIRECTIVE_LOCATION_ADDED, (loc, name)

            for d in _diff_arguments(
                old_directive.argument_map,
                new_directive.argument_map,
                "directive {}".format(name),
            ):
                yield d

    for name in new.directives.keys():
        if name not in old.directives:
            yield SchemaChange.DIRECTIVE_ADDED, (name,)


def _diff_arguments(
    old_args: Mapping[str, Argument],
    new_args: Mapping[str, Argument],
    context: str,
) -> Iterator[DiffParams]:
    for name, old_arg in old_args.items():
        try:
            new_arg = new_args[name]
        except KeyError:
            yield SchemaChange.ARG_REMOVED, (name, context)
        else:
            if not _is_safe_input_type_change(old_arg.type, new_arg.type):
                yield (
                    SchemaChange.ARG_CHANGED_TYPE,
                    (name, context, old_arg.type, new_arg.type),
                )
            elif (
                (old_arg.has_default_value and not new_arg.has_default_value)
                or (not old_arg.has_default_value and new_arg.has_default_value)
                or (
                    old_arg.has_default_value
                    and old_arg.default_value != new_arg.default_value
                )
            ):
                yield SchemaChange.ARG_DEFAULT_VALUE_CHANGE, (name, context)

    for name, new_arg in new_args.items():
        try:
            old_arg = old_args[name]
        except KeyError:
            if new_arg.required:
                yield SchemaChange.REQUIRED_ARG_ADDED, (name, context)
            else:
                yield SchemaChange.OPTIONAL_ARG_ADDED, (name, context)


def _is_safe_input_type_change(
    old_type: GraphQLType, new_type: GraphQLType
) -> bool:
    if isinstance(old_type, NamedType):
        return (
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


def _diff_object_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_object, new_object in _old_and_new(old, new, ObjectType):
        parent = "type {}".format(name)

        for field_name, old_field in old_object.field_map.items():
            try:
                new_field = new_object.field_map[field_name]
            except KeyError:
                yield SchemaChange.FIELD_REMOVED, (field_name, parent)
            else:
                for d in _diff_field(old_field, new_field, parent):
                    yield d

        for field_name in new_object.field_map.keys():
            if field_name not in old_object.field_map:
                yield SchemaChange.FIELD_ADDED, (field_name, parent)

        old_interfaces = set(i.name for i in old_object.interfaces)
        new_interfaces = set(i.name for i in new_object.interfaces)

        for i in old_interfaces - new_interfaces:
            yield SchemaChange.TYPE_REMOVED_FROM_INTERFACE, (name, i)

        for i in new_interfaces - old_interfaces:
            if i in old.implementations:
                yield SchemaChange.TYPE_ADDED_TO_INTERFACE, (name, i)


def _diff_interface_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_interface, new_interface in _old_and_new(
        old, new, InterfaceType
    ):
        parent = "interface {}".format(name)

        for field_name, old_field in old_interface.field_map.items():
            try:
                new_field = new_interface.field_map[field_name]
            except KeyError:
                yield SchemaChange.FIELD_REMOVED, (field_name, parent)
            else:
                for d in _diff_field(old_field, new_field, parent):
                    yield d

        for field_name in new_interface.field_map.keys():
            if field_name not in old_interface.field_map:
                yield SchemaChange.FIELD_ADDED, (field_name, parent)


def _diff_field(old: Field, new: Field, parent: str) -> Iterator[DiffParams]:
    if not _is_safe_output_type_change(old.type, new.type):
        yield (
            SchemaChange.FIELD_CHANGED_TYPE,
            (old.name, parent, old.type, new.type),
        )

    for d in _diff_arguments(
        old.argument_map,
        new.argument_map,
        "field {} of {}".format(old.name, parent),
    ):
        yield d

    if old.deprecated:
        if not new.deprecated:
            yield SchemaChange.FIELD_DEPRECATION_REMOVED, (old.name, parent)
        elif old.deprecation_reason != new.deprecation_reason:
            yield (
                SchemaChange.FIELD_DEPRECATION_REASON_CHANGED,
                (old.name, parent),
            )
    elif new.deprecated:
        yield SchemaChange.FIELD_DEPRECATED, (old.name, parent)


def _diff_input_types(old: Schema, new: Schema) -> Iterator[DiffParams]:
    for name, old_type, new_type in _old_and_new(old, new, InputObjectType):
        for d in _diff_input_fields(
            old_type.field_map, new_type.field_map, name
        ):
            yield d


def _diff_input_fields(
    old_fields: Mapping[str, InputField],
    new_fields: Mapping[str, InputField],
    parent: str,
) -> Iterator[DiffParams]:
    for name, old_field in old_fields.items():
        try:
            new_field = new_fields[name]
        except KeyError:
            yield SchemaChange.INPUT_FIELD_REMOVED, (name, parent)
        else:
            if not _is_safe_input_type_change(old_field.type, new_field.type):
                yield (
                    SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                    (name, parent, old_field.type, new_field.type),
                )
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
                yield (
                    SchemaChange.INPUT_FIELD_DEFAULT_VALUE_CHANGE,
                    (name, parent),
                )

    for name, new_field in new_fields.items():
        try:
            old_field = old_fields[name]
        except KeyError:
            if new_field.required:
                yield SchemaChange.REQUIRED_INPUT_FIELD_ADDED, (name, parent)
            else:
                yield SchemaChange.OPTIONAL_INPUT_FIELD_ADDED, (name, parent)
