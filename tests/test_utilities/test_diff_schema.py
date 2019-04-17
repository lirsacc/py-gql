# -*- coding: utf-8 -*-

import pytest

from py_gql.builders import build_schema
from py_gql.utilities.differ import (
    SchemaChange,
    SchemaChangeSeverity,
    diff_schema,
)

DIFF_TEST_GROUPS = [
    (
        "add_and_remove_types",
        build_schema(
            """
            type Type1 { field1: String }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            type Type2 { field1: String }
            type Query { field1: String }
            """
        ),
        [
            (SchemaChange.TYPE_REMOVED, "Type Type1 was removed."),
            (SchemaChange.TYPE_ADDED, "Type Type2 was added."),
        ],
    ),
    (
        "type_changed_type",
        build_schema(
            """
            interface Type1 { field1: String }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            type ObjectType { field1: String }
            union Type1 = ObjectType
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.TYPE_CHANGED_KIND,
                "Type1 changed from an Interface type to a Union type.",
            )
        ],
    ),
    (
        "object_fields",
        build_schema(
            """
            type TypeA { field1: String }
            type TypeB { field1: String }
            type Type1 {
                field1: TypeA
                field2: String
                field3: String
                field4: TypeA
                field6: String
                field7: [String]
                field8: Int
                field9: Int!
                field10: [Int]!
                field11: Int
                field12: [Int]
                field13: [Int!]
                field14: [Int]
                field15: [[Int]]
                field16: Int!
                field17: [Int]
                field18: [[Int!]!]
                field19: Int @deprecated
                field20: Int @deprecated(reason: "test")
                field21: Int
            }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            type TypeA { field1: String }
            type TypeB { field1: String }
            type Type1 {
                field1: TypeA
                field3: Boolean
                field4: TypeB
                field5: String
                field6: [String]
                field7: String
                field8: Int!
                field9: Int
                field10: [Int]
                field11: [Int]!
                field12: [Int!]
                field13: [Int]
                field14: [[Int]]
                field15: [Int]
                field16: [Int]!
                field17: [Int]!
                field18: [[Int!]]
                field19: Int
                field20: Int @deprecated(reason: "Tes")
                field21: Int @deprecated
            }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.FIELD_REMOVED,
                "Field field2 was removed from type Type1.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field3 of type Type1 has changed type from String to Boolean.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field4 of type Type1 has changed type from TypeA to TypeB.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field6 of type Type1 has changed type from String to [String].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field7 of type Type1 has changed type from [String] to String.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field9 of type Type1 has changed type from Int! to Int.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field10 of type Type1 has changed type from [Int]! to [Int].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field11 of type Type1 has changed type from Int to [Int]!.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field12 of type Type1 has changed type from [Int] to [Int!].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field14 of type Type1 has changed type from [Int] to [[Int]].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field15 of type Type1 has changed type from [[Int]] to [Int].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field16 of type Type1 has changed type from Int! to [Int]!.",
            ),
            (
                SchemaChange.FIELD_DEPRECATION_REMOVED,
                "Field field19 of type Type1 is no longer deprecated.",
            ),
            (
                SchemaChange.FIELD_DEPRECATION_REASON_CHANGED,
                "Field field20 of type Type1 has changed deprecation reason.",
            ),
            (
                SchemaChange.FIELD_DEPRECATED,
                "Field field21 of type Type1 was deprecated.",
            ),
            (SchemaChange.FIELD_ADDED, "Field field5 was added to type Type1."),
        ],
    ),
    (
        "interface_fields",
        build_schema(
            """
            type TypeA { field1: String }
            type TypeB { field1: String }
            interface Type1 {
                field1: TypeA
                field2: String
                field3: String
                field4: TypeA
                field6: String
                field7: [String]
                field8: Int
                field9: Int!
                field10: [Int]!
                field11: Int
                field12: [Int]
                field13: [Int!]
                field14: [Int]
                field15: [[Int]]
                field16: Int!
                field17: [Int]
                field18: [[Int!]!]
                field19: Int @deprecated
                field20: Int @deprecated(reason: "test")
                field21: Int
            }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            type TypeA { field1: String }
            type TypeB { field1: String }
            interface Type1 {
                field1: TypeA
                field3: Boolean
                field4: TypeB
                field5: String
                field6: [String]
                field7: String
                field8: Int!
                field9: Int
                field10: [Int]
                field11: [Int]!
                field12: [Int!]
                field13: [Int]
                field14: [[Int]]
                field15: [Int]
                field16: [Int]!
                field17: [Int]!
                field18: [[Int!]]
                field19: Int
                field20: Int @deprecated(reason: "Tes")
                field21: Int @deprecated
            }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.FIELD_REMOVED,
                "Field field2 was removed from interface Type1.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field3 of interface Type1 has changed type "
                "from String to Boolean.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field4 of interface Type1 has changed type from TypeA to TypeB.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field6 of interface Type1 has changed type "
                "from String to [String].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field7 of interface Type1 has changed type "
                "from [String] to String.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field9 of interface Type1 has changed type from Int! to Int.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field10 of interface Type1 has changed type "
                "from [Int]! to [Int].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field11 of interface Type1 has changed type from Int to [Int]!.",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field12 of interface Type1 has changed type "
                "from [Int] to [Int!].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field14 of interface Type1 has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field15 of interface Type1 has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                SchemaChange.FIELD_CHANGED_TYPE,
                "Field field16 of interface Type1 has changed type "
                "from Int! to [Int]!.",
            ),
            (
                SchemaChange.FIELD_DEPRECATION_REMOVED,
                "Field field19 of interface Type1 is no longer deprecated.",
            ),
            (
                SchemaChange.FIELD_DEPRECATION_REASON_CHANGED,
                "Field field20 of interface Type1 has changed deprecation reason.",
            ),
            (
                SchemaChange.FIELD_DEPRECATED,
                "Field field21 of interface Type1 was deprecated.",
            ),
            (
                SchemaChange.FIELD_ADDED,
                "Field field5 was added to interface Type1.",
            ),
        ],
    ),
    (
        "detect_type_removed_or_added_from_union_type",
        build_schema(
            """
            type Type1 { field1: String }
            type Type2 { field1: String }
            union UnionType1 = Type1 | Type2
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            type Type1 { field1: String }
            type Type3 { field1: String }
            union UnionType1 = Type1 | Type3
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.TYPE_REMOVED_FROM_UNION,
                "Type2 was removed from union type UnionType1.",
            ),
            (
                SchemaChange.TYPE_ADDED_TO_UNION,
                "Type3 was added to union type UnionType1.",
            ),
        ],
    ),
    (
        "detect_enum_value_changes",
        build_schema(
            """
            enum EnumType1 {
                VALUE0
                VALUE1
                VALUE2
                VALUE3 @deprecated(reason: "Foo")
                VALUE4 @deprecated
                VALUE5
            }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            enum EnumType1 {
                VALUE0
                VALUE2
                VALUE3 @deprecated(reason: "Bar")
                VALUE4
                VALUE5 @deprecated
                VALUE6
            }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.VALUE_REMOVED_FROM_ENUM,
                "VALUE1 was removed from enum type EnumType1.",
            ),
            (
                SchemaChange.VALUE_ADDED_TO_ENUM,
                "VALUE6 was added to enum type EnumType1.",
            ),
            (
                SchemaChange.ENUM_VALUE_DEPRECATION_REMOVED,
                "VALUE4 from enum type EnumType1 is no longer deprecated.",
            ),
            (
                SchemaChange.ENUM_VALUE_DEPRECATED,
                "VALUE5 from enum type EnumType1 was deprecated.",
            ),
            (
                SchemaChange.ENUM_VALUE_DEPRECATION_REASON_CHANGE,
                "VALUE3 from enum type EnumType1 has changed deprecation reason.",
            ),
        ],
    ),
    (
        "detect_added_and_removed_directives_and_location",
        build_schema(
            """
            directive @fooDirective on SCHEMA
            directive @bazDirective on FIELD_DEFINITION | OBJECT
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            directive @barDirective on SCHEMA
            directive @bazDirective on FIELD_DEFINITION | SCALAR
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.DIRECTIVE_REMOVED,
                "Directive fooDirective was removed.",
            ),
            (SchemaChange.DIRECTIVE_ADDED, "Directive barDirective was added."),
            (
                SchemaChange.DIRECTIVE_LOCATION_REMOVED,
                "Location OBJECT was removed from directive bazDirective.",
            ),
            (
                SchemaChange.DIRECTIVE_LOCATION_ADDED,
                "Location SCALAR was added to directive bazDirective.",
            ),
        ],
    ),
    (
        "directive_arguments",
        build_schema(
            """
            directive @fooDirective(
                arg1: String
                arg2: String
                arg3: [String]
                arg4: String
                arg5: String!
                arg6: String!
                arg7: [Int]!
                arg8: Int
                arg9: [Int]
                arg10: [Int!]
                arg11: [Int]
                arg12: [[Int]]
                arg13: Int!
                arg14: [[Int]!]
                arg15: [[Int]!]
                arg16: String = "test"
            ) on SCHEMA
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            directive @fooDirective(
                arg1: Int
                arg2: [String]
                arg3: String
                arg4: String!
                arg5: Int
                arg6: Int!
                arg7: [Int]
                arg8: [Int]!
                arg9: [Int!]
                arg10: [Int]
                arg11: [[Int]]
                arg12: [Int]
                arg13: [Int]!
                arg14: [[Int]]
                arg15: [[Int!]!]
                arg16: String = "Test"
                arg17: Int!,
                arg18: Int! = 42,
                arg19: Int,
            ) on SCHEMA
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg1 of directive fooDirective has changed type "
                "from String to Int.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg2 of directive fooDirective has changed type "
                "from String to [String].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg3 of directive fooDirective has changed type "
                "from [String] to String.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg4 of directive fooDirective has changed type "
                "from String to String!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg5 of directive fooDirective has changed type "
                "from String! to Int.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg6 of directive fooDirective has changed type "
                "from String! to Int!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg8 of directive fooDirective has changed type "
                "from Int to [Int]!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg9 of directive fooDirective has changed type "
                "from [Int] to [Int!].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg11 of directive fooDirective has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg12 of directive fooDirective has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg13 of directive fooDirective has changed type "
                "from Int! to [Int]!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg15 of directive fooDirective has changed type "
                "from [[Int]!] to [[Int!]!].",
            ),
            (
                SchemaChange.ARG_DEFAULT_VALUE_CHANGE,
                "Argument arg16 of directive fooDirective has changed default value.",
            ),
            (
                SchemaChange.REQUIRED_ARG_ADDED,
                "Required argument arg17 was added to directive fooDirective.",
            ),
            (
                SchemaChange.OPTIONAL_ARG_ADDED,
                "Optional argument arg18 was added to directive fooDirective.",
            ),
            (
                SchemaChange.OPTIONAL_ARG_ADDED,
                "Optional argument arg19 was added to directive fooDirective.",
            ),
        ],
    ),
    (
        "field_arguments",
        build_schema(
            """
            type Foo {
                field1(
                    arg1: String
                    arg2: String
                    arg3: [String]
                    arg4: String
                    arg5: String!
                    arg6: String!
                    arg7: [Int]!
                    arg8: Int
                    arg9: [Int]
                    arg10: [Int!]
                    arg11: [Int]
                    arg12: [[Int]]
                    arg13: Int!
                    arg14: [[Int]!]
                    arg15: [[Int]!]
                    arg16: String = "test"
                ) : String
            }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            type Foo {
                field1(
                    arg1: Int
                    arg2: [String]
                    arg3: String
                    arg4: String!
                    arg5: Int
                    arg6: Int!
                    arg7: [Int]
                    arg8: [Int]!
                    arg9: [Int!]
                    arg10: [Int]
                    arg11: [[Int]]
                    arg12: [Int]
                    arg13: [Int]!
                    arg14: [[Int]]
                    arg15: [[Int!]!]
                    arg16: String = "Test"
                    arg17: Int!,
                    arg18: Int! = 42,
                    arg19: Int,
                ) : String
            }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg1 of field field1 of type Foo has changed type "
                "from String to Int.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg2 of field field1 of type Foo has changed type "
                "from String to [String].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg3 of field field1 of type Foo has changed type "
                "from [String] to String.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg4 of field field1 of type Foo has changed type "
                "from String to String!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg5 of field field1 of type Foo has changed type "
                "from String! to Int.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg6 of field field1 of type Foo has changed type "
                "from String! to Int!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg8 of field field1 of type Foo has changed type "
                "from Int to [Int]!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg9 of field field1 of type Foo has changed type "
                "from [Int] to [Int!].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg11 of field field1 of type Foo has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg12 of field field1 of type Foo has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg13 of field field1 of type Foo has changed type "
                "from Int! to [Int]!.",
            ),
            (
                SchemaChange.ARG_CHANGED_TYPE,
                "Argument arg15 of field field1 of type Foo has changed type "
                "from [[Int]!] to [[Int!]!].",
            ),
            (
                SchemaChange.ARG_DEFAULT_VALUE_CHANGE,
                "Argument arg16 of field field1 of type Foo has changed default value.",
            ),
            (
                SchemaChange.REQUIRED_ARG_ADDED,
                "Required argument arg17 was added to field field1 of type Foo.",
            ),
            (
                SchemaChange.OPTIONAL_ARG_ADDED,
                "Optional argument arg18 was added to field field1 of type Foo.",
            ),
            (
                SchemaChange.OPTIONAL_ARG_ADDED,
                "Optional argument arg19 was added to field field1 of type Foo.",
            ),
        ],
    ),
    (
        "interface_addition_and_removal",
        build_schema(
            """
            interface Iface1 { field1: String }
            interface Iface2 { field1: String }
            type Type1 implements Iface1 { field1: String }
            type Type2 implements Iface2 { field1: String }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            interface Iface1 { field1: String }
            interface Iface2 { field1: String }
            type Type1 implements Iface2 { field1: String }
            type Type2 implements Iface1 { field1: String }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.TYPE_REMOVED_FROM_INTERFACE,
                "Type1 no longer implements Iface1.",
            ),
            (
                SchemaChange.TYPE_ADDED_TO_INTERFACE,
                "Type1 now implements Iface2.",
            ),
            (
                SchemaChange.TYPE_REMOVED_FROM_INTERFACE,
                "Type2 no longer implements Iface2.",
            ),
            (
                SchemaChange.TYPE_ADDED_TO_INTERFACE,
                "Type2 now implements Iface1.",
            ),
        ],
    ),
    (
        "input_fields",
        build_schema(
            """
            input InputType1 {
                field1: String
                field2: String = "test"
                field3: String
            }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            input InputType1 {
                field1: String
                field2: String = "Test"
                requiredField: Int!
                optionalField1: Boolean
                optionalField2: Boolean! = false
            }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.REQUIRED_INPUT_FIELD_ADDED,
                "Required input field requiredField was added to InputType1.",
            ),
            (
                SchemaChange.OPTIONAL_INPUT_FIELD_ADDED,
                "Optional argument optionalField1 was added to InputType1.",
            ),
            (
                SchemaChange.OPTIONAL_INPUT_FIELD_ADDED,
                "Optional argument optionalField2 was added to InputType1.",
            ),
            (
                SchemaChange.INPUT_FIELD_DEFAULT_VALUE_CHANGE,
                "Input field field2 of InputType1 has changed default value.",
            ),
            (
                SchemaChange.INPUT_FIELD_REMOVED,
                "Input field field3 was removed from InputType1.",
            ),
        ],
    ),
    (
        "input_field_changed_type",
        build_schema(
            """
            input InputType1 {
                field1: String
                field2: Boolean
                field3: [String]
                field4: String!
                field5: String
                field6: [Int]
                field7: [Int]!
                field8: Int
                field9: [Int]
                field10: [Int!]
                field11: [Int]
                field12: [[Int]]
                field13: Int!
                field14: [[Int]!]
                field15: [[Int]!]
            }
            type Query { field1: String }
            """
        ),
        build_schema(
            """
            input InputType1 {
                field1: Int
                field3: String
                field4: String
                field5: String!
                field6: [Int]!
                field7: [Int]
                field8: [Int]!
                field9: [Int!]
                field10: [Int]
                field11: [[Int]]
                field12: [Int]
                field13: [Int]!
                field14: [[Int]]
                field15: [[Int!]!]
            }
            type Query { field1: String }
            """
        ),
        [
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field1 of InputType1 has changed type "
                "from String to Int.",
            ),
            (
                SchemaChange.INPUT_FIELD_REMOVED,
                "Input field field2 was removed " "from InputType1.",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field3 of InputType1 has changed type "
                "from [String] to String.",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field5 of InputType1 has changed type "
                "from String to String!.",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field6 of InputType1 has changed type "
                "from [Int] to [Int]!.",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field8 of InputType1 has changed type "
                "from Int to [Int]!.",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field9 of InputType1 has changed type "
                "from [Int] to [Int!].",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field11 of InputType1 has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field12 of InputType1 has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field13 of InputType1 has changed type "
                "from Int! to [Int]!.",
            ),
            (
                SchemaChange.INPUT_FIELD_CHANGED_TYPE,
                "Input field field15 of InputType1 has changed type "
                "from [[Int]!] to [[Int!]!].",
            ),
        ],
    ),
]


def _cached_diff_schema(s1, s2, cache={}):
    try:
        return cache[(s1, s2)]
    except KeyError:
        return list(diff_schema(s1, s2))


# Split each group in multiple tests for easier reporting.
@pytest.mark.parametrize(
    "old_schema, new_schema, expected_diff",
    [
        pytest.param(
            old_schema, new_schema, diff, id="{}:{}".format(group, diff[1])
        )
        for group, old_schema, new_schema, diffs in DIFF_TEST_GROUPS
        for diff in diffs
    ],
)
def test_diffs(old_schema, new_schema, expected_diff):
    diffs = _cached_diff_schema(old_schema, new_schema)

    # Run pytest with -s to see the actual diffs in a somewhat more readable
    # format than the assertion error.
    print("\nTest case:")
    print(
        '(SchemaChange.{}, "{}"),'.format(
            expected_diff[0]._name, expected_diff[1]
        )
    )
    print("Found diffs:")
    for diff in diffs:
        print('(SchemaChange.{}, "{}"),'.format(diff[0]._name, diff[1]))

    assert expected_diff in diffs


def test_detects_no_change_in_same_schema(fixture_file):
    schema = build_schema(fixture_file("github-schema.graphql"))
    assert [] == list(diff_schema(schema, schema))


@pytest.mark.parametrize(
    "old_schema,new_schema",
    [
        (
            """
            type Query { foo: Int }
            """,
            """
            type Query { foo: Int! }
            """,
        ),
        (
            """
            input Input { foo: Int! }
            type Query { foo: Int }
            """,
            """
            input Input { foo: Int }
            type Query { foo: Int }
            """,
        ),
    ],
)
def test_no_incompatible_changes(old_schema, new_schema):
    assert [] == list(
        diff_schema(
            build_schema(old_schema),
            build_schema(new_schema),
            min_severity=SchemaChangeSeverity.DANGEROUS,
        )
    )


def test_minimum_severity():
    assert [(SchemaChange.TYPE_REMOVED, "Type Type1 was removed.")] == list(
        diff_schema(
            build_schema(
                """
                type Type1 { field1: String }
                type Query { field1: String }
                """
            ),
            build_schema(
                """
                type Type2 { field1: String }
                type Query { field1: String }
                """
            ),
            min_severity=SchemaChangeSeverity.BREAKING,
        )
    )
