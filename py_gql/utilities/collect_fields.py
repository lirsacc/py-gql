# -*- coding: utf-8 -*-
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Union,
)

from .._utils import OrderedDict
from ..lang import ast
from ..schema import (
    GraphQLAbstractType,
    IncludeDirective,
    ObjectType,
    Schema,
    SkipDirective,
)
from ..utilities import directive_arguments

GroupedFields = Dict[str, List[ast.Field]]

InclueCallable = Callable[
    [Union[ast.Field, ast.InlineFragment, ast.FragmentSpread]], bool
]


def collect_fields(
    schema: Schema,
    object_type: ObjectType,
    selections: Sequence[ast.Selection],
    fragments: Mapping[str, ast.FragmentDefinition],
    variables: Mapping[str, Any],
    _already_processed_fragments: Optional[Set[str]] = None,
) -> GroupedFields:
    """
    """
    _already_processed_fragments = _already_processed_fragments or set()
    grouped_fields = OrderedDict()  # type: GroupedFields

    for selection in selections:
        if isinstance(selection, ast.Field):
            if _skip_selection(selection, variables):
                continue

            key = selection.response_name

            if key not in grouped_fields:
                grouped_fields[key] = []

            grouped_fields[key].append(selection)

        elif isinstance(selection, ast.InlineFragment):
            if _skip_selection(
                selection, variables
            ) or not _fragment_type_applies(schema, object_type, selection):
                continue

            _collect_fragment_fields(
                schema,
                object_type,
                fragments,
                variables,
                selection,
                grouped_fields,
                _already_processed_fragments,
            )

        elif isinstance(selection, ast.FragmentSpread):
            name = selection.name.value
            fragment = fragments[name]

            if (
                _skip_selection(selection, variables)
                or name in _already_processed_fragments
                or not _fragment_type_applies(schema, object_type, fragment)
            ):
                continue

            _collect_fragment_fields(
                schema,
                object_type,
                fragments,
                variables,
                fragment,
                grouped_fields,
                _already_processed_fragments,
            )
            _already_processed_fragments.add(name)

    return grouped_fields


def _collect_fragment_fields(
    schema: Schema,
    object_type: ObjectType,
    fragments: Mapping[str, ast.FragmentDefinition],
    variables: Mapping[str, Any],
    fragment: Union[ast.FragmentDefinition, ast.InlineFragment],
    grouped_fields: GroupedFields,
    processed_fragments: Set[str],
) -> None:
    fragment_grouped_fields = collect_fields(
        schema,
        object_type,
        fragment.selection_set.selections,
        fragments,
        variables,
        processed_fragments,
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


def _skip_selection(
    node: Union[ast.Field, ast.InlineFragment, ast.FragmentSpread],
    variables: Mapping[str, Any],
) -> bool:
    skip = directive_arguments(SkipDirective, node, variables=variables)
    include = directive_arguments(IncludeDirective, node, variables=variables)
    skipped = skip is not None and skip["if"]
    included = include is None or include["if"]
    return skipped or (not included)
