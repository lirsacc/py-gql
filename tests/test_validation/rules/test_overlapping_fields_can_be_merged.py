# -*- coding: utf-8 -*-
""" Test specified rule in isolation. """

# Tests were adapted from the one in the GraphQLJS reference implementation,
# as our version exits early not all of the expected errors are aplicable but
# they conserved as comments for reference.
# Tests related to suggestion list are kept for reference but skipped as this
# feature is not implemented.

import pytest

from py_gql.validation import OverlappingFieldsCanBeMergedChecker
from .._test_utils import assert_checker_validation_result as run_test


def test_unique_fields(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment uniqueFields on Dog {
        name
        nickname
    }
    ''')


def test_identical_fields(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment mergeIdenticalFields on Dog {
        name
        name
    }
    ''')


def test_identical_fields_with_identical_args(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment mergeIdenticalFieldsWithIdenticalArgs on Dog {
        doesKnowCommand(dogCommand: SIT)
        doesKnowCommand(dogCommand: SIT)
    }
    ''')


def test_identical_fields_with_identical_directives(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment mergeSameFieldsWithSameDirectives on Dog {
        name @include(if: true)
        name @include(if: true)
    }
    ''')


def test_different_args_with_different_aliases(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment differentArgsWithDifferentAliases on Dog {
        knowsSit: doesKnowCommand(dogCommand: SIT)
        knowsDown: doesKnowCommand(dogCommand: DOWN)
    }
    ''')


def test_different_directives_with_different_aliases(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment differentDirectivesWithDifferentAliases on Dog {
        nameIfTrue: name @include(if: true)
        nameIfFalse: name @include(if: false)
    }
    ''')


def test_different_skip_include_directives_accepted(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment differentDirectivesWithDifferentAliases on Dog {
        name @include(if: true)
        name @include(if: false)
    }
    ''')


def test_same_aliases_with_different_field_targets(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment sameAliasesWithDifferentFieldTargets on Dog {
        fido: name
        fido: nickname
    }
    ''', [
        'Field(s) "fido" conflict because "name" and "nickname" are '
        'different fields. Use different aliases on the fields to fetch '
        'both if this was intentional.'
    ], [[(68, 78), (87, 101)]])


def test_same_aliases_allowed_on_non_overlapping_fields(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment sameAliasesWithDifferentFieldTargets on Pet {
        ... on Dog {
            name
        }
        ... on Cat {
            name: nickname
        }
    }
    ''')


def test_alias_masking_direct_field_access(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment aliasMaskingDirectFieldAccess on Dog {
        name: nickname
        name
    }
    ''', [
        'Field(s) "name" conflict because "nickname" and "name" are different '
        'fields. Use different aliases on the fields to fetch both if this '
        'was intentional.'
    ], [[(61, 75), (84, 88)]])


def test_different_args_second_adds_an_argument(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment conflictingArgs on Dog {
        doesKnowCommand
        doesKnowCommand(dogCommand: HEEL)
    }
    ''', [
        'Field(s) "doesKnowCommand" conflict because "doesKnowCommand" '
        'and "doesKnowCommand" have different arguments. Use different '
        'aliases on the fields to fetch both if this was intentional.'
    ])


def test_different_args_second_missing_an_argument(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment conflictingArgs on Dog {
        doesKnowCommand(dogCommand: SIT)
        doesKnowCommand
    }
    ''', [
        'Field(s) "doesKnowCommand" conflict because "doesKnowCommand" '
        'and "doesKnowCommand" have different arguments. Use different '
        'aliases on the fields to fetch both if this was intentional.'
    ])


def test_conflicting_args(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment conflictingArgs on Dog {
        doesKnowCommand(dogCommand: SIT)
        doesKnowCommand(dogCommand: HEEL)
    }
    ''', [
        'Field(s) "doesKnowCommand" conflict because "doesKnowCommand" '
        'and "doesKnowCommand" have different arguments. Use different '
        'aliases on the fields to fetch both if this was intentional.'
    ])


def test_allows_different_args_where_no_conflict_is_possible(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment conflictingArgs on Pet {
        ... on Dog {
            name(surname: true)
        }
        ... on Cat {
            name
        }
    }
    ''')


def test_encounters_conflict_in_fragments(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        ...A
        ...B
    }
    fragment A on Type {
        x: a
    }
    fragment B on Type {
        x: b
    }
    ''', [
        'Field(s) "x" conflict because "a" and "b" are different fields. Use '
        'different aliases on the fields to fetch both if this was intentional.'
    ], [[(72, 76), (116, 120)]])


def test_reports_each_conflict_once(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        f1 {
            ...A
            ...B
        }
        f2 {
            ...B
            ...A
        }
        f3 {
            ...A
            ...B
            x: c
        }
    }
    fragment A on Type {
        x: a
    }
    fragment B on Type {
        x: b
    }
    ''', [
        'Field(s) "x" conflict because "a" and "b" are different fields. '
        'Use different aliases on the fields to fetch both if this was '
        'intentional.',
        'Field(s) "x" conflict because "c" and "a" are different fields. '
        'Use different aliases on the fields to fetch both if this was '
        'intentional.',
        'Field(s) "x" conflict because "c" and "b" are different fields. '
        'Use different aliases on the fields to fetch both if this was '
        'intentional.'
    ], [
        [(234, 238), (278, 282)],
        [(180, 184), (234, 238)],
        [(180, 184), (278, 282)]
    ])


def test_deep_conflict(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        field {
            x: a
        },
        field {
            x: b
        }
    }
    ''', [
        'Field(s) "field" conflict because subfields "x" conflict '
        '("a" and "b" are different fields). Use different aliases '
        'on the fields to fetch both if this was intentional.'
    ], [
        [(15, 49), (35, 39), (59, 93), (79, 83)]
    ])


def test_deep_conflict_with_multiple_issues(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        field {
            x: a
            y: c
        },
        field {
            x: b
            y: d
        }
    }
    ''', [
        'Field(s) "field" conflict because subfields "x" conflict '
        '("a" and "b" are different fields) and subfields "y" conflict '
        '("c" and "d" are different fields). Use different aliases on the '
        'fields to fetch both if this was intentional.'
    ], [
        [(15, 66), (35, 39), (52, 56), (76, 127), (96, 100), (113, 117)]
    ])


def test_very_deep_conflict(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        field {
            deepField {
                x: a
            }
        },
        field {
            deepField {
                x: b
            }
        }
    }
    ''', [
        'Field(s) "field" conflict because subfields "deepField" conflict '
        '(subfields "x" conflict ("a" and "b" are different fields)). '
        'Use different aliases on the fields to fetch both if this was '
        'intentional.'
    ], [
        [(15, 91), (35, 81), (63, 67), (101, 177), (121, 167), (149, 153)]
    ])


def test_reports_deep_conflict_to_nearest_common_ancestor(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        field {
            deepField {
                x: a
            }
            deepField {
                x: b
            }
        },
        field {
            deepField {
                y
            }
        }
    }
    ''', [
        'Field(s) "deepField" conflict because subfields "x" conflict '
        '("a" and "b" are different fields). Use different aliases on the '
        'fields to fetch both if this was intentional.'
    ], [
        [(35, 81), (63, 67), (94, 140), (122, 126)]
    ])


def test_reports_deep_conflict_to_nearest_common_ancestor_in_fragments(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        field {
            ...F
        }
        field {
            ...F
        }
    }
    fragment F on T {
        deepField {
            deeperField {
                x: a
            }
            deeperField {
                x: b
            }
        },
        deepField {
            deeperField {
                y
            }
        }
    }
    ''', [
        'Field(s) "deeperField" conflict because subfields "x" conflict '
        '("a" and "b" are different fields). Use different aliases on the '
        'fields to fetch both if this was intentional.'
    ], [
        [(153, 201), (183, 187), (214, 262), (244, 248)]
    ])


def test_reports_deep_conflict_in_nested_fragments(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        field {
            ...F
        }
        field {
            ...I
        }
    }
    fragment F on T {
        x: a
        ...G
    }
    fragment G on T {
        y: c
    }
    fragment I on T {
        y: d
        ...J
    }
    fragment J on T {
        x: b
    }
    ''', [
        'Field(s) "field" conflict because subfields "y" conflict ("c" and '
        '"d" are different fields) and subfields "x" conflict ("a" and "b" '
        'are different fields). '
        'Use different aliases on the fields to fetch both if this was '
        'intentional.'
    ])


def test_ignores_unknown_fragments(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
      field
      ...Unknown
      ...Known
    }

    fragment Known on T {
      field
      ...OtherUnknown
    }
    ''')


def test_conflicting_return_types_which_potentially_overlap(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
     {
        someBox {
            ...on IntBox {
                scalar
            }
            ...on NonNullStringBox1 {
                scalar
            }
        }
    }
    ''', [
        'Field(s) "scalar" conflict because they return '
        'conflicting types Int and String!. Use different aliases on the '
        'fields to fetch both if this was intentional.'
    ])


def test_compatible_return_shapes_on_different_return_types(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on SomeBox {
            deepBox {
                unrelatedField
            }
            }
            ... on StringBox {
                deepBox {
                    unrelatedField
                }
            }
        }
    }
    ''')


def test_disallows_differing_return_types_despite_no_overlap(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                scalar
            }
            ... on StringBox {
                scalar
            }
        }
    }
    ''', [
        'Field(s) "scalar" conflict because they return conflicting types '
        'Int and String. Use different aliases on the fields to fetch both '
        'if this was intentional.'
    ])


def test_reports_correctly_when_a_non_exclusive_follows_an_exclusive(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                deepBox {
                   ...X
                }
            }
        }
        someBox {
            ... on StringBox {
                deepBox {
                ...Y
                }
            }
        }
        memoed: someBox {
            ... on IntBox {
                deepBox {
                   ...X
                }
            }
        }
        memoed: someBox {
            ... on StringBox {
                deepBox {
                   ...Y
                }
            }
        }
        other: someBox {
            ...X
        }
        other: someBox {
            ...Y
        }
    }
    fragment X on SomeBox {
        scalar
    }
    fragment Y on SomeBox {
        scalar: unrelatedField
    }
    ''', [
        'Field(s) "other" conflict because subfields "scalar" conflict '
        '("scalar" and "unrelatedField" are different fields). Use different '
        'aliases on the fields to fetch both if this was intentional.'
    ], [
        [(586, 629), (724, 730), (638, 681), (773, 795)]
    ])


def test_disallows_differing_return_type_nullability_despite_no_overlap(
        schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on NonNullStringBox1 {
                scalar
            }
            ... on StringBox {
                scalar
            }
        }
    }
    ''', [
        'Field(s) "scalar" conflict because they return conflicting types '
        'String! and String. Use different aliases on the fields to fetch '
        'both if this was intentional.'
    ], [
        [(80, 86), (148, 154)]
    ])


def test_disallows_differing_return_type_list_despite_no_overlap_0(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                box: listStringBox {
                    scalar
                }
            }
            ... on StringBox {
                box: stringBox {
                   scalar
                }
            }
        }
    }
    ''', [
        'Field(s) "box" conflict because they return conflicting types '
        '[StringBox] and StringBox. Use different aliases on the fields to '
        'fetch both if this was intentional.'
    ])


def test_disallows_differing_return_type_list_despite_no_overlap_1(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                box: stringBox {
                   scalar
                }
            }
            ... on StringBox {
                box: listStringBox {
                   scalar
                }
            }
        }
    }
    ''', [
        'Field(s) "box" conflict because they return conflicting types '
        'StringBox and [StringBox]. Use different aliases on the fields to '
        'fetch both if this was intentional.'
    ])


def test_disallows_differing_subfields(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                box: stringBox {
                    val: scalar
                    val: unrelatedField
                }
            }
            ... on StringBox {
                box: stringBox {
                   val: scalar
                }
            }
        }
    }
    ''', [
        'Field(s) "val" conflict because "scalar" and "unrelatedField" are '
        'different fields. Use different aliases on the fields to fetch both '
        'if this was intentional.'
    ])


def test_disallows_differing_deep_return_types_despite_no_overlap(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                box: stringBox {
                   scalar
                }
            }
            ... on StringBox {
                box: intBox {
                   scalar
                }
            }
        }
    }
    ''', [
        'Field(s) "box" conflict because subfields "scalar" conflict '
        '(they return conflicting types String and Int). Use different '
        'aliases on the fields to fetch both if this was intentional.'
    ])


def test_allows_non_conflicting_overlaping_types(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ... on IntBox {
                scalar: unrelatedField
            }
            ... on StringBox {
                scalar
            }
        }
    }
    ''')


def test_same_wrapped_scalar_return_types(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ...on NonNullStringBox1 {
                scalar
            }
            ...on NonNullStringBox2 {
                scalar
            }
        }
    }
    ''')


def test_allows_inline_typeless_fragments(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    {
        a
        ... {
            a
        }
    }
    ''')


def test_compares_deep_types_including_list(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        connection {
            ...edgeID
            edges {
                node {
                    id: name
                }
            }
        }
    }

    fragment edgeID on Connection {
        edges {
            node {
                id
            }
        }
    }
    ''', [
        'Field(s) "edges" conflict because subfields "node" conflict '
        '(subfields "id" conflict ("name" and "id" are different fields)). '
        'Use different aliases on the fields to fetch both if this was '
        'intentional.'
    ])


def test_ignores_unknown_types(schema_2):
    run_test(OverlappingFieldsCanBeMergedChecker, schema_2, '''
    {
        someBox {
            ...on UnknownType {
                scalar
            }
            ...on NonNullStringBox2 {
                scalar
            }
        }
    }
    ''')


@pytest.mark.skip('Irrelevant')
def test_error_message_contains_hint_for_alias_conflict(schema):
    pass


@pytest.mark.skip('Irrelevant')
def test_works_for_field_names_that_are_js_keywords(schema):
    pass


def test_does_not_infinite_loop_on_recursive_fragment(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment fragA on Human { name, relatives { name, ...fragA } }
    ''')


def test_does_not_infinite_loop_on_immediately_recursive_fragment(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment fragA on Human { name, ...fragA }
    ''')


def test_does_not_infinite_loop_on_transitively_recursive_fragment(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment fragA on Human { name, ...fragB }
    fragment fragB on Human { name, ...fragC }
    fragment fragC on Human { name, ...fragA }
    ''')


def test_finds_invalid_case_even_with_immediately_recursive_fragment(schema):
    run_test(OverlappingFieldsCanBeMergedChecker, schema, '''
    fragment sameAliasesWithDifferentFieldTargets on Dog {
        ...sameAliasesWithDifferentFieldTargets
        fido: name
        fido: nickname
    }
    ''', [
        'Field(s) "fido" conflict because "name" and "nickname" are different '
        'fields. Use different aliases on the fields to fetch both if this '
        'was intentional.'
    ])
