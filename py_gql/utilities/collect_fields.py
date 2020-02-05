# -*- coding: utf-8 -*-
import fnmatch
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    TypeVar,
    Union,
)
from typing.re import Pattern

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

T = TypeVar("T")
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
    _seen_fragments: Optional[Set[str]] = None,
) -> GroupedFields:
    """
    """
    _seen_fragments = _seen_fragments or set()
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

            _merge(
                collect_fields(
                    schema,
                    object_type,
                    selection.selection_set.selections,
                    fragments,
                    variables,
                    _seen_fragments,
                ),
                into=grouped_fields,
            )

        elif isinstance(selection, ast.FragmentSpread):
            name = selection.name.value
            # This should ususally be used after validation (given a document
            # and schema are required) and so we expect fragments to be present.
            fragment = fragments[name]

            if (
                _skip_selection(selection, variables)
                or name in _seen_fragments
                or not _fragment_type_applies(schema, object_type, fragment)
            ):
                continue

            _merge(
                collect_fields(
                    schema,
                    object_type,
                    fragment.selection_set.selections,
                    fragments,
                    variables,
                    _seen_fragments,
                ),
                into=grouped_fields,
            )
            _seen_fragments.add(name)

    return grouped_fields


def collect_fields_untyped(
    selections: Sequence[ast.Selection],
    fragments: Mapping[str, ast.FragmentDefinition],
    variables: Mapping[str, Any],
    _seen_fragments: Optional[Set[str]] = None,
) -> GroupedFields:
    """
    """
    _seen_fragments = _seen_fragments or set()
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
            if _skip_selection(selection, variables):
                continue

            _merge(
                collect_fields_untyped(
                    selection.selection_set.selections,
                    fragments,
                    variables,
                    _seen_fragments,
                ),
                into=grouped_fields,
            )

        elif isinstance(selection, ast.FragmentSpread):
            name = selection.name.value
            if _skip_selection(selection, variables) or name in _seen_fragments:
                continue

            try:
                fragment = fragments[name]
            except KeyError:
                # As we don't typecheck or validate, this could go through
                # invalid fragments.
                continue

            _merge(
                collect_fields_untyped(
                    fragment.selection_set.selections,
                    fragments,
                    variables,
                    _seen_fragments,
                ),
                into=grouped_fields,
            )

            _seen_fragments.add(name)

    return grouped_fields


def _merge(groups: Dict[str, List[T]], *, into: Dict[str, List[T]]) -> None:
    for key, collected in groups.items():
        if key not in into:
            into[key] = []

        into[key].extend(collected)


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


def selected_fields(
    field: ast.Field,
    *,
    fragments: Mapping[str, ast.FragmentDefinition],
    variables: Mapping[str, Any],
    maxdepth: Optional[int] = 1,
    pattern: Optional[Union[str, Pattern]] = None,
    _path: Optional[List[str]] = None
) -> List[str]:
    """Extract a list of fieldpaths from an object field and provided
    fragments.

    If ``maxdepth`` is 0 or higher than 1, subfields will be traversed
    recursively and exposed as a ``/`` separated path. For example,
    considering the root field of the following document:

    .. code-block:: graphql

        query {
            field {
                foo {
                    bar {
                        baz
                    }
                }
            }
        }

    Calling ``selected_fields(..., maxdepth=0)`` will yield ``['foo',
    'foo/bar', 'foo/bar/baz']``.

    Args:
        field: Root field
        fragments: Document fragments
        variables: Operation variables
        maxdepth: Control how deep the traversal should go.
            If set to 0, then traversal will proceed as deep as possible.
        pattern: Filter string used to control which fields are returned.
            If this is passed as a string, it will be compiled into a regex
            through the :py:mod:`fnmatch` module.
    """

    if field.selection_set is None:
        return []

    _path = _path or []
    fieldnames = []

    collected = collect_fields_untyped(
        field.selection_set.selections, fragments, variables
    )

    if isinstance(pattern, str):
        pattern = re.compile(fnmatch.translate(pattern))

    for _, fields in collected.items():

        child_field = fields[0]
        child_path = [*_path, child_field.name.value]
        joined = "/".join(child_path)

        if pattern is None or pattern.match(joined):
            fieldnames.append(joined)

        if (not maxdepth) or len(_path) < (maxdepth - 1):
            fieldnames.extend(
                selected_fields(
                    child_field,
                    fragments=fragments,
                    variables=variables,
                    maxdepth=maxdepth,
                    pattern=pattern,
                    _path=child_path,
                )
            )

    return fieldnames
