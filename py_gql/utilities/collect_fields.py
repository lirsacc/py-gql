# -*- coding: utf-8 -*-
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Set, Union

from .._utils import OrderedDict
from ..lang import ast
from ..schema import GraphQLAbstractType, ObjectType, Schema

GroupedFields = Dict[str, List[ast.Field]]

InclueCallable = Callable[
    [Union[ast.Field, ast.InlineFragment, ast.FragmentSpread]], bool
]


def collect_fields(
    schema: Schema,
    object_type: ObjectType,
    selections: Sequence[ast.Selection],
    fragments: Mapping[str, ast.FragmentDefinition],
    _already_processed_fragments: Optional[Set[str]] = None,
    _skip: InclueCallable = lambda _: True,
) -> GroupedFields:
    """
    """
    _already_processed_fragments = _already_processed_fragments or set()
    grouped_fields = OrderedDict()  # type: GroupedFields

    for selection in selections:
        if isinstance(selection, ast.Field):
            if _skip(selection):
                continue

            key = selection.response_name

            if key not in grouped_fields:
                grouped_fields[key] = []

            grouped_fields[key].append(selection)

        elif isinstance(selection, ast.InlineFragment):
            if _skip(selection) or not _fragment_type_applies(
                schema, object_type, selection
            ):
                continue

            _collect_fragment_fields(
                schema,
                object_type,
                fragments,
                selection,
                grouped_fields,
                _already_processed_fragments,
                _skip,
            )

        elif isinstance(selection, ast.FragmentSpread):
            name = selection.name.value
            fragment = fragments[name]

            if (
                _skip(selection)
                or name in _already_processed_fragments
                or not _fragment_type_applies(schema, object_type, fragment)
            ):
                continue

            _collect_fragment_fields(
                schema,
                object_type,
                fragments,
                fragment,
                grouped_fields,
                _already_processed_fragments,
                _skip,
            )
            _already_processed_fragments.add(name)

    return grouped_fields


def _collect_fragment_fields(
    schema: Schema,
    object_type: ObjectType,
    fragments: Mapping[str, ast.FragmentDefinition],
    fragment: Union[ast.FragmentDefinition, ast.InlineFragment],
    grouped_fields: GroupedFields,
    processed_fragments: Set[str],
    skip: InclueCallable,
) -> None:
    fragment_grouped_fields = collect_fields(
        schema,
        object_type,
        fragment.selection_set.selections,
        fragments,
        processed_fragments,
        skip,
    )
    for key, collected in fragment_grouped_fields.items():
        if key not in grouped_fields:
            grouped_fields[key] = []

        grouped_fields[key].extend(collected)


def _fragment_type_applies(
    schema: Schema,
    object_type: ObjectType,
    fragment: Union[ast.InlineFragment, ast.FragmentDefinition],
) -> bool:
    type_condition = fragment.type_condition
    if not type_condition:
        return True

    fragment_type = schema.get_type_from_literal(type_condition)
    return (fragment_type == object_type) or (
        isinstance(fragment_type, GraphQLAbstractType)
        and schema.is_possible_type(fragment_type, object_type)
    )
