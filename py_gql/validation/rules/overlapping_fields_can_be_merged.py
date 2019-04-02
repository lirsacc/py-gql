# -*- coding: utf-8 -*-

from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple, TypeVar

from ..._utils import OrderedDict, deduplicate, flatten
from ...exc import UnknownType
from ...lang import ast as _ast
from ...schema import (
    Field,
    GraphQLType,
    InterfaceType,
    ObjectType,
    Schema,
    is_leaf_type,
    unwrap_type,
)
from ...schema.types import ListType, NonNullType
from ..visitors import ValidationVisitor

T = TypeVar("T")
G = TypeVar("G")

WrappingType = (ListType, NonNullType)

FieldDef = Tuple[Optional[GraphQLType], _ast.Field, Optional[Field]]
FieldMap = Dict[str, List[FieldDef]]
FieldsAndFragments = Tuple[FieldMap, List[str]]

Conflict = Tuple[str, str, Sequence[_ast.Node]]


class Context:
    def __init__(
        self,
        schema: Schema,
        fields_and_fragments: Dict[_ast.SelectionSet, FieldsAndFragments],
        compared_fragment_pairs: Set[Tuple[Tuple[str, str], bool]],
        fragments: Dict[str, _ast.FragmentDefinition],
    ):
        self.schema = schema
        self.fields_and_fragments = fields_and_fragments
        self.compared_fragment_pairs = compared_fragment_pairs
        self.fragments = fragments


def _permutations(lst: Sequence[T]) -> Iterator[Tuple[T, T]]:
    """
    Symmetric permutations of a list

    >>> list(_permutations([1, 2, 3]))
    [(1, 2), (1, 3), (2, 3)]
    """
    for i, item_1 in enumerate(lst):
        for item_2 in lst[i + 1 :]:
            yield item_1, item_2


def _cross(iter_1: Sequence[T], iter_2: Sequence[G]) -> Iterator[Tuple[T, G]]:
    """
    Cross product of 2 sequences

    >>> list(_cross([1, 2, 3], [4, 5, 6]))
    [(1, 4), (1, 5), (1, 6), (2, 4), (2, 5), (2, 6), (3, 4), (3, 5), (3, 6)]
    """
    for a in iter_1:
        for b in iter_2:
            yield a, b


def _at(
    lst: Sequence[T], index: int, default: Optional[T] = None
) -> Optional[T]:
    """
    Safely extract value from a list at a given index.

    >>> _at([], 0) is None
    True
    >>> _at([1], 2) is None
    True
    """
    try:
        return lst[index]
    except IndexError:
        return default


def _type_from_ast(schema, node):
    try:
        return schema.get_type_from_literal(node)
    except UnknownType:
        return None


class OverlappingFieldsCanBeMergedChecker(ValidationVisitor):
    """
    A selection set is only valid if all fields (including spreading any
    fragments) either correspond to distinct response names or can be merged
    without ambiguity.
    """

    def __init__(self, schema, type_info):
        super(OverlappingFieldsCanBeMergedChecker, self).__init__(
            schema, type_info
        )
        self.ctx = Context(self.schema, {}, set(), {})

    def enter_document(self, node):
        # Should happen before visitng any selection set
        self.ctx.fragments.update(
            {
                d.name.value: d
                for d in node.definitions
                if isinstance(d, _ast.FragmentDefinition)
            }
        )

    def enter_selection_set(self, node):
        conflicts = find_conflicts_within_selection_set(
            self.ctx, node, self.type_info.parent_type
        )  # type: List[Conflict]

        for response_name, reason, locs in conflicts:
            self.add_error(
                'Field(s) "%s" conflict because %s. Use different aliases on '
                "the fields to fetch both if this was intentional."
                % (response_name, reason),
                locs,
            )


def find_conflicts_within_selection_set(
    ctx: Context, selection_set: _ast.SelectionSet, parent_type: GraphQLType
) -> List[Conflict]:
    """
    Find all conflicts found "within" a selection set, including those found
    via spreading in fragments. Called when visiting each SelectionSet in the
    GraphQL Document.


    Algorithm:
    ==========

    Conflicts occur when two fields exist in a query which will produce the same
    response name, but represent differing values, thus creating a conflict.
    The algorithm below finds all conflicts via making a series of comparisons
    between fields. In order to compare as few fields as possible, this makes a
    series of comparisons "within" sets of fields and "between" sets of fields.

    Given any selection set, a collection produces both a set of fields by
    also including all inline fragments, as well as a list of fragments
    referenced by fragment spreads.

    A) Each selection set represented in the document first compares "within"
       its collected set of fields, finding any conflicts between every pair of
       overlapping fields.
       Note: This is the *only time* that a the fields "within" a set are
       compared to each other. After this only fields "between" sets are
       compared.

    B) Also, if any fragment is referenced in a selection set, then a
       comparison is made "between" the original set of fields and the
       referenced fragment.

    C) Also, if multiple fragments are referenced, then comparisons
       are made "between" each referenced fragment.

    D) When comparing "between" a set of fields and a referenced fragment, first
       a comparison is made between each field in the original set of fields and
       each field in the the referenced set of fields.

    E) Also, if any fragment is referenced in the referenced selection set,
       then a comparison is made "between" the original set of fields and the
       referenced fragment (recursively referring to step D).

    F) When comparing "between" two fragments, first a comparison is made
       between each field in the first referenced set of fields and each field
       in the the second referenced set of fields.

    G) Also, any fragments referenced by the first must be compared to the
       second, and any fragments referenced by the second must be compared to
       the first (recursively referring to step F).

    H) When comparing two fields, if both have selection sets, then a comparison
       is made "between" both selection sets, first comparing the set of fields
       in the first selection set with the set of fields in the second.

    I) Also, if any fragment is referenced in either selection set, then a
       comparison is made "between" the other set of fields and the
       referenced fragment.

    J) Also, if two fragments are referenced in both selection sets, then a
       comparison is made "between" the two fragments.
    """
    # Implementation note: all functions detecting conflicts are generators
    # to keep the code simple and only this one collects the generators into a
    # list.
    conflicts = []  # type: List[Conflict]

    field_map, fragment_names = _fields_and_fragments(
        ctx, parent_type, selection_set
    )

    # (A) Find find all conflicts "within" the fields of this selection set.
    for conflict in _conflicts_within(ctx, field_map):
        conflicts.append(conflict)

    compared_fragments = set()  # type: Set[str]
    for fragment_name in fragment_names:
        # (B) Then collect conflicts between these fields and those represented
        # by each spread fragment name found.
        for conflict in _conflicts_between_fields_and_fragment(
            ctx, False, field_map, fragment_name, compared_fragments
        ):
            conflicts.append(conflict)

    # (C) Then compare this fragment with all other fragments found in this
    # selection set to collect conflicts between fragments spread together.
    # This compares each item in the list of fragment names to every other
    # item in that same list (except for itself).
    for frag_1, frag_2 in _permutations(fragment_names):
        for conflict in _conflicts_between_fragments(
            ctx, False, frag_1, frag_2
        ):
            conflicts.append(conflict)

    return conflicts


def _fields_and_fragments(
    ctx: Context,
    parent_type: Optional[GraphQLType],
    selection_set: _ast.SelectionSet,
) -> FieldsAndFragments:
    """
    Given a selection set, return the collection of fields (a mapping
    of response name to field nodes and definitions) as well as a list of
    fragment names referenced via fragment spreads.
    """
    cached = ctx.fields_and_fragments.get(selection_set)
    if cached is not None:
        return cached

    # A field map is an ordered keyed collection, where each key represents a
    # response name and the value at that key is a list of all fields which
    # provide that response name. For every response name, if there are
    # multiple fields, they must be compared to find a potential conflict.
    field_map, fragment_names = _collect_fields_and_fragments(
        ctx, parent_type, selection_set
    )

    ctx.fields_and_fragments[selection_set] = (field_map, fragment_names)
    return field_map, list(deduplicate(fragment_names))


def _referenced_fields_and_fragments(
    ctx: Context, fragment: _ast.FragmentDefinition
) -> FieldsAndFragments:
    """
    Given a fragment definition, return the represented collection of
    fields as well as a list of nested fragment names referenced via
    fragment spreads.
    """
    cached = ctx.fields_and_fragments.get(fragment.selection_set)
    if cached is not None:
        return cached

    fragment_type = _type_from_ast(ctx.schema, fragment.type_condition)
    return _fields_and_fragments(ctx, fragment_type, fragment.selection_set)


def _collect_fields_and_fragments(
    ctx: Context,
    parent_type: Optional[GraphQLType],
    selection_set: _ast.SelectionSet,
    node_and_defs: Optional[FieldMap] = None,
    fragment_names: Optional[List[str]] = None,
) -> FieldsAndFragments:

    if node_and_defs is None:
        node_and_defs = OrderedDict()
    if fragment_names is None:
        fragment_names = []

    for selection in selection_set.selections:
        if isinstance(selection, _ast.Field):
            fieldname = selection.name.value

            fielddef = (
                parent_type.field_map.get(fieldname, None)
                if isinstance(parent_type, (ObjectType, InterfaceType))
                else None
            )

            response_name = (
                selection.alias.value
                if selection.alias and selection.alias.value
                else fieldname
            )

            if response_name not in node_and_defs:
                node_and_defs[response_name] = []

            node_and_defs[response_name].append(
                (parent_type, selection, fielddef)
            )

        elif isinstance(selection, _ast.FragmentSpread):
            fragment_names.append(selection.name.value)

        elif isinstance(selection, _ast.InlineFragment):
            type_condition = selection.type_condition

            inline_fragment_type = (
                _type_from_ast(ctx.schema, type_condition)
                if type_condition
                else parent_type
            )

            _collect_fields_and_fragments(
                ctx,
                inline_fragment_type,
                selection.selection_set,
                node_and_defs=node_and_defs,
                fragment_names=fragment_names,
            )

    return node_and_defs, fragment_names


def _conflicts_within(ctx: Context, field_map: FieldMap) -> Iterator[Conflict]:
    """
    Collect all Conflicts "within" one collection of fields.
    """
    for response_name, fields in field_map.items():
        # This compares every field in the list to every other field in this
        # list (except to itself). If the list only has one item, nothing
        # needs to be compared.
        for field_1, field_2 in _permutations(fields):
            conflict = _find_conflict(
                ctx,
                False,  # within one collection is never mutually exclusive
                response_name,
                field_1,
                field_2,
            )
            if conflict:
                yield conflict


def _conflicts_between(
    ctx: Context,
    parents_mutually_exclusive: bool,
    field_map_1: FieldMap,
    field_map_2: FieldMap,
) -> Iterator[Conflict]:
    """
    Collect all Conflicts between two collections of fields. This is
    similar to, but different from the `collectConflictsWithin` function above.
    This check assumes that `collectConflictsWithin` has already been called
    on each provided collection of fields. This is true because this
    validator traverses each individual selection set.
    """
    for response_name, fields_1 in field_map_1.items():
        fields_2 = field_map_2.get(response_name)
        if fields_2 is None:
            continue

        for field_1 in fields_1:
            for field_2 in fields_2:
                conflict = _find_conflict(
                    ctx,
                    parents_mutually_exclusive,
                    response_name,
                    field_1,
                    field_2,
                )
                if conflict:
                    yield conflict


def _conflicts_between_fields_and_fragment(
    ctx: Context,
    mutually_exclusive: bool,
    field_map: FieldMap,
    fragment_name: str,
    compared_fragments: Set[str],
) -> Iterator[Conflict]:
    """
    Collect all conflicts found between a set of fields and a fragment
    reference including via spreading in any nested fragments.
    """
    # Memoize so a fragment is not compared for conflicts more than once.
    if fragment_name in compared_fragments:
        return

    compared_fragments.add(fragment_name)
    fragment_def = ctx.fragments.get(fragment_name)
    if not fragment_def:
        return

    ff = _referenced_fields_and_fragments(ctx, fragment_def)
    fragment_field_map, fragment_fragment_names = ff

    # ??
    # Do not compare a fragment's fieldMap to itself.
    if field_map is fragment_field_map:
        return

    # (D) First collect any conflicts between the provided collection of fields
    # and the collection of fields represented by the given fragment.
    for c in _conflicts_between(
        ctx, mutually_exclusive, field_map, fragment_field_map
    ):
        yield c

    # (E) Then collect any conflicts between the provided collection of fields
    # and any fragment names found in the given fragment.
    for fragment in fragment_fragment_names:
        for c in _conflicts_between_fields_and_fragment(
            ctx, mutually_exclusive, field_map, fragment, compared_fragments
        ):
            yield c


def _conflicts_between_fragments(
    ctx: Context,
    mutually_exclusive: bool,
    fragment_1: Optional[str],
    fragment_2: Optional[str],
) -> Iterator[Conflict]:
    """
    Collect all conflicts found between two fragments, including via
    spreading in any nested fragments.
    """
    if (not fragment_1) or (not fragment_2) or fragment_1 == fragment_2:
        return

    # Avoid comparing fragments twice and double reporting
    # The comparison order doesn't matter, hence the weird cache key
    cache_key = (tuple(sorted([fragment_1, fragment_2])), mutually_exclusive)
    if cache_key in ctx.compared_fragment_pairs:
        return

    ctx.compared_fragment_pairs.add(cache_key)  # type: ignore

    def_1 = ctx.fragments.get(fragment_1)
    def_2 = ctx.fragments.get(fragment_2)

    if def_1 is None or def_2 is None:
        return

    fields_1, fragments_1 = _referenced_fields_and_fragments(ctx, def_1)
    fields_2, fragments_2 = _referenced_fields_and_fragments(ctx, def_2)

    # (F) First, collect all conflicts between these two collections of fields
    # (not including any nested fragments).
    for c in _conflicts_between(ctx, mutually_exclusive, fields_1, fields_2):
        yield c

    # (G) Then collect conflicts between the first fragment and any nested
    # fragments spread in the second fragment.
    for i, fragment in enumerate(fragments_1):
        for c in _conflicts_between_fragments(
            ctx, mutually_exclusive, fragment, _at(fragment_2, i)
        ):
            yield c

    # (G) Then collect conflicts between the second fragment and any nested
    # fragments spread in the first fragment.
    for i, fragment in enumerate(fragments_2):
        for c in _conflicts_between_fragments(
            ctx, mutually_exclusive, _at(fragment_1, i), fragment
        ):
            yield c


def _find_conflict(
    ctx: Context,
    parents_mutually_exclusive: bool,
    response_name: str,
    field_1: FieldDef,
    field_2: FieldDef,
) -> Optional[Conflict]:
    """
    Determines if there is a conflict between two particular fields,
    including comparing their sub-fields.
    """
    parent_1, node_1, def_1 = field_1
    parent_2, node_2, def_2 = field_2

    # If it is known that two fields could not possibly apply at the same
    # time, due to the parent types, then it is safe to permit them to diverge
    # in aliased field or arguments used as they will not present any ambiguity
    # by differing.
    # It is known that two parent types could never overlap if they are
    # different Object types. Interface or Union types might overlap - if not
    # in the current state of the schema, then perhaps in some future version,
    # thus may not safely diverge.
    mutually_exclusive = parents_mutually_exclusive or (
        parent_1 != parent_2
        and isinstance(parent_1, ObjectType)
        and isinstance(parent_2, ObjectType)
    )

    # The return type for each field.
    type_1 = def_1.type if def_1 else None
    type_2 = def_2.type if def_2 else None
    name_1 = node_1.name.value
    name_2 = node_2.name.value

    if not mutually_exclusive:
        # Two aliases must refer to the same field.
        if name_1 != name_2:
            reason = '"%s" and "%s" are different fields' % (name_1, name_2)
            return response_name, reason, (node_1, node_2)

        # Two field calls must have the same arguments.
        if not _same_arguments(node_1.arguments or [], node_2.arguments or []):
            reason = '"%s" and "%s" have different arguments' % (name_1, name_2)
            return response_name, reason, (node_1, node_2)

    if type_1 and type_2 and _types_conflict(type_1, type_2):
        reason = "they return conflicting types %s and %s" % (type_1, type_2)
        return response_name, reason, (node_1, node_2)

    # Collect and compare sub-fields. Use the same "visited fragment names" list
    # for both collections so fields in a fragment reference are never
    # compared to themselves.
    if node_1.selection_set and node_2.selection_set:
        subconflicts = list(
            _conflicts_between_subselections(
                ctx,
                mutually_exclusive,
                unwrap_type(type_1) if type_1 else None,
                node_1.selection_set,
                unwrap_type(type_2) if type_2 else None,
                node_2.selection_set,
            )
        )
        if subconflicts:
            reason = " and ".join(
                [
                    'subfields "%s" conflict (%s)' % (name, reason_)
                    for name, reason_, _ in subconflicts
                ]
            )
            nodes = list(
                sorted(
                    [node_1, node_2]
                    + list(flatten(nodes for _, _, nodes in subconflicts)),
                    key=lambda n: n.loc,
                )
            )
            return response_name, reason, nodes

    return None


def _conflicts_between_subselections(
    ctx: Context,
    mutually_exclusive: bool,
    parent_type_1: Optional[GraphQLType],
    node_1: _ast.SelectionSet,
    parent_type_2: Optional[GraphQLType],
    node_2: _ast.SelectionSet,
) -> Iterator[Conflict]:
    """
    Find all conflicts found between two selection sets, including those
    found via spreading in fragments. Called when determining if conflicts
    exist between the sub-fields of two overlapping fields.
    """

    field_map_1, fragments_1 = _fields_and_fragments(ctx, parent_type_1, node_1)
    field_map_2, fragments_2 = _fields_and_fragments(ctx, parent_type_2, node_2)

    # (H) First, collect all conflicts between these two collections of field.
    for c in _conflicts_between(
        ctx, mutually_exclusive, field_map_1, field_map_2
    ):
        yield c

    # (I) Then collect conflicts between the first collection of fields and
    # those referenced by each fragment name associated with the second.
    for fragment in fragments_2:
        for c in _conflicts_between_fields_and_fragment(
            ctx, mutually_exclusive, field_map_1, fragment, set()
        ):
            yield c

    # (I) Then collect conflicts between the second collection of fields and
    # those referenced by each fragment name associated with the first.
    for fragment in fragments_1:
        for c in _conflicts_between_fields_and_fragment(
            ctx, mutually_exclusive, field_map_2, fragment, set()
        ):
            yield c

    # (J) Also collect conflicts between any fragment names by the first and
    # fragment names by the second. This compares each item in the first set of
    # names to each item in the second set of names.
    for fragment_1, fragment_2 in _cross(fragments_1, fragments_2):
        for c in _conflicts_between_fragments(
            ctx, mutually_exclusive, fragment_1, fragment_2
        ):
            yield c


def _same_arguments(
    args_1: List[_ast.Argument], args_2: List[_ast.Argument]
) -> bool:
    """
    Given two lists of arguments, check all arguments have the same name
    and values with no extra / missing argument.
    """
    if len(args_1) != len(args_2):
        return False

    s1 = sorted(args_1, key=lambda a: a.name.value)
    s2 = sorted(args_2, key=lambda a: a.name.value)

    return all(
        (
            (
                a1.name.value == a2.name.value
                and type(a1.value) == type(a2.value)  # noqa: E721
                and a1.value.value == a2.value.value  # type: ignore
            )
            for a1, a2 in zip(s1, s2)
        )
    )


def _types_conflict(type_1: GraphQLType, type_2: GraphQLType) -> bool:
    """
    Two types conflict if both types could not apply to a value
    simultaneously. Composite types are ignored as their individual field
    types will be compared later recursively. However List and Non-Null types
    must match.
    """
    if isinstance(type_1, WrappingType) or isinstance(type_2, WrappingType):
        return type(type_1) != type(type_2) or _types_conflict(
            type_1.type, type_2.type  # type: ignore
        )

    if is_leaf_type(type_1) or is_leaf_type(type_2):
        return type_1 != type_2

    return False
