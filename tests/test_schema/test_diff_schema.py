# -*- coding: utf-8 -*-

import pytest

from py_gql.schema.differ import (
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
    SchemaChangeSeverity,
    TypeAdded,
    TypeAddedToInterface,
    TypeAddedToUnion,
    TypeChangedKind,
    TypeRemoved,
    TypeRemovedFromInterface,
    TypeRemovedFromUnion,
    diff_schema,
)
from py_gql.sdl import build_schema

GROUPED_TEST_CASES = [
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
            (TypeRemoved, "Type Type1 was removed."),
            (TypeAdded, "Type Type2 was added."),
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
        [(TypeChangedKind, "Type1 changed from Interface type to Union type.")],
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
            (FieldRemoved, "Field field2 was removed from type Type1."),
            (
                FieldChangedType,
                "Field field3 of type Type1 has changed type from String to Boolean.",
            ),
            (
                FieldChangedType,
                "Field field4 of type Type1 has changed type from TypeA to TypeB.",
            ),
            (
                FieldChangedType,
                "Field field6 of type Type1 has changed type from String to [String].",
            ),
            (
                FieldChangedType,
                "Field field7 of type Type1 has changed type from [String] to String.",
            ),
            (
                FieldChangedType,
                "Field field9 of type Type1 has changed type from Int! to Int.",
            ),
            (
                FieldChangedType,
                "Field field10 of type Type1 has changed type from [Int]! to [Int].",
            ),
            (
                FieldChangedType,
                "Field field11 of type Type1 has changed type from Int to [Int]!.",
            ),
            (
                FieldChangedType,
                "Field field12 of type Type1 has changed type from [Int] to [Int!].",
            ),
            (
                FieldChangedType,
                "Field field14 of type Type1 has changed type from [Int] to [[Int]].",
            ),
            (
                FieldChangedType,
                "Field field15 of type Type1 has changed type from [[Int]] to [Int].",
            ),
            (
                FieldChangedType,
                "Field field16 of type Type1 has changed type from Int! to [Int]!.",
            ),
            (
                FieldDeprecationRemoved,
                "Field field19 of type Type1 is no longer deprecated.",
            ),
            (
                FieldDeprecationReasonChanged,
                "Field field20 of type Type1 has changed deprecation reason.",
            ),
            (FieldDeprecated, "Field field21 of type Type1 was deprecated."),
            (FieldAdded, "Field field5 was added to type Type1."),
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
            (FieldRemoved, "Field field2 was removed from interface Type1."),
            (
                FieldChangedType,
                "Field field3 of interface Type1 has changed type "
                "from String to Boolean.",
            ),
            (
                FieldChangedType,
                "Field field4 of interface Type1 has changed type from TypeA to TypeB.",
            ),
            (
                FieldChangedType,
                "Field field6 of interface Type1 has changed type "
                "from String to [String].",
            ),
            (
                FieldChangedType,
                "Field field7 of interface Type1 has changed type "
                "from [String] to String.",
            ),
            (
                FieldChangedType,
                "Field field9 of interface Type1 has changed type from Int! to Int.",
            ),
            (
                FieldChangedType,
                "Field field10 of interface Type1 has changed type "
                "from [Int]! to [Int].",
            ),
            (
                FieldChangedType,
                "Field field11 of interface Type1 has changed type from Int to [Int]!.",
            ),
            (
                FieldChangedType,
                "Field field12 of interface Type1 has changed type "
                "from [Int] to [Int!].",
            ),
            (
                FieldChangedType,
                "Field field14 of interface Type1 has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                FieldChangedType,
                "Field field15 of interface Type1 has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                FieldChangedType,
                "Field field16 of interface Type1 has changed type "
                "from Int! to [Int]!.",
            ),
            (
                FieldDeprecationRemoved,
                "Field field19 of interface Type1 is no longer deprecated.",
            ),
            (
                FieldDeprecationReasonChanged,
                "Field field20 of interface Type1 has changed deprecation reason.",
            ),
            (
                FieldDeprecated,
                "Field field21 of interface Type1 was deprecated.",
            ),
            (FieldAdded, "Field field5 was added to interface Type1."),
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
                TypeRemovedFromUnion,
                "Type2 was removed from union type UnionType1.",
            ),
            (TypeAddedToUnion, "Type3 was added to union type UnionType1."),
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
            (EnumValueRemoved, "VALUE1 was removed from enum EnumType1."),
            (EnumValueAdded, "VALUE6 was added to enum EnumType1."),
            (
                EnumValueDeprecationRemoved,
                "VALUE4 from enum EnumType1 is no longer deprecated.",
            ),
            (EnumValueDeprecated, "VALUE5 from enum EnumType1 was deprecated."),
            (
                EnumValueDeprecationReasonChanged,
                "VALUE3 from enum EnumType1 has changed deprecation reason.",
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
            (DirectiveRemoved, "Directive fooDirective was removed."),
            (DirectiveAdded, "Directive barDirective was added."),
            (
                DirectiveLocationRemoved,
                "Location OBJECT was removed from directive bazDirective.",
            ),
            (
                DirectiveLocationAdded,
                "Location SCALAR was added to directive bazDirective.",
            ),
        ],
    ),
    (
        "directive_arguments",
        build_schema(
            """
            directive @fooDirective(
                arg0: String,
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
                DirectiveArgumentRemoved,
                "Argument arg0 was removed from directive fooDirective.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg1 of directive fooDirective has changed type "
                "from String to Int.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg2 of directive fooDirective has changed type "
                "from String to [String].",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg3 of directive fooDirective has changed type "
                "from [String] to String.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg4 of directive fooDirective has changed type "
                "from String to String!.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg5 of directive fooDirective has changed type "
                "from String! to Int.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg6 of directive fooDirective has changed type "
                "from String! to Int!.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg8 of directive fooDirective has changed type "
                "from Int to [Int]!.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg9 of directive fooDirective has changed type "
                "from [Int] to [Int!].",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg11 of directive fooDirective has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg12 of directive fooDirective has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg13 of directive fooDirective has changed type "
                "from Int! to [Int]!.",
            ),
            (
                DirectiveArgumentChangedType,
                "Argument arg15 of directive fooDirective has changed type "
                "from [[Int]!] to [[Int!]!].",
            ),
            (
                DirectiveArgumentDefaultValueChange,
                "Argument arg16 of directive fooDirective has changed default value.",
            ),
            (
                DirectiveArgumentAdded,
                "Required argument arg17 was added to directive fooDirective.",
            ),
            (
                DirectiveArgumentAdded,
                "Optional argument arg18 was added to directive fooDirective.",
            ),
            (
                DirectiveArgumentAdded,
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
                    arg0: String,
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
                FieldArgumentRemoved,
                "Argument arg0 was removed from field field1 of type Foo.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg1 of field field1 of type Foo has changed type "
                "from String to Int.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg2 of field field1 of type Foo has changed type "
                "from String to [String].",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg3 of field field1 of type Foo has changed type "
                "from [String] to String.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg4 of field field1 of type Foo has changed type "
                "from String to String!.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg5 of field field1 of type Foo has changed type "
                "from String! to Int.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg6 of field field1 of type Foo has changed type "
                "from String! to Int!.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg8 of field field1 of type Foo has changed type "
                "from Int to [Int]!.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg9 of field field1 of type Foo has changed type "
                "from [Int] to [Int!].",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg11 of field field1 of type Foo has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg12 of field field1 of type Foo has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg13 of field field1 of type Foo has changed type "
                "from Int! to [Int]!.",
            ),
            (
                FieldArgumentChangedType,
                "Argument arg15 of field field1 of type Foo has changed type "
                "from [[Int]!] to [[Int!]!].",
            ),
            (
                FieldArgumentDefaultValueChange,
                "Argument arg16 of field field1 of type Foo has changed default value.",
            ),
            (
                FieldArgumentAdded,
                "Required argument arg17 was added to field field1 of type Foo.",
            ),
            (
                FieldArgumentAdded,
                "Optional argument arg18 was added to field field1 of type Foo.",
            ),
            (
                FieldArgumentAdded,
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
            (TypeRemovedFromInterface, "Type1 no longer implements Iface1."),
            (TypeAddedToInterface, "Type1 now implements Iface2."),
            (TypeRemovedFromInterface, "Type2 no longer implements Iface2."),
            (TypeAddedToInterface, "Type2 now implements Iface1."),
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
                InputFieldAdded,
                "Required input field requiredField was added to InputType1.",
            ),
            (
                InputFieldAdded,
                "Optional input field optionalField1 was added to InputType1.",
            ),
            (
                InputFieldAdded,
                "Optional input field optionalField2 was added to InputType1.",
            ),
            (
                InputFieldDefaultValueChange,
                "Input field field2 of InputType1 has changed default value.",
            ),
            (
                InputFieldRemoved,
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
                InputFieldChangedType,
                "Input field field1 of InputType1 has changed type "
                "from String to Int.",
            ),
            (
                InputFieldRemoved,
                "Input field field2 was removed " "from InputType1.",
            ),
            (
                InputFieldChangedType,
                "Input field field3 of InputType1 has changed type "
                "from [String] to String.",
            ),
            (
                InputFieldChangedType,
                "Input field field5 of InputType1 has changed type "
                "from String to String!.",
            ),
            (
                InputFieldChangedType,
                "Input field field6 of InputType1 has changed type "
                "from [Int] to [Int]!.",
            ),
            (
                InputFieldChangedType,
                "Input field field8 of InputType1 has changed type "
                "from Int to [Int]!.",
            ),
            (
                InputFieldChangedType,
                "Input field field9 of InputType1 has changed type "
                "from [Int] to [Int!].",
            ),
            (
                InputFieldChangedType,
                "Input field field11 of InputType1 has changed type "
                "from [Int] to [[Int]].",
            ),
            (
                InputFieldChangedType,
                "Input field field12 of InputType1 has changed type "
                "from [[Int]] to [Int].",
            ),
            (
                InputFieldChangedType,
                "Input field field13 of InputType1 has changed type "
                "from Int! to [Int]!.",
            ),
            (
                InputFieldChangedType,
                "Input field field15 of InputType1 has changed type "
                "from [[Int]!] to [[Int!]!].",
            ),
        ],
    ),
]


def assert_change_found(changes, expected):

    hashed_changes = [(c.__class__, c.message) for c in changes]

    print("\nTest case:")
    print('{}("{}"),'.format(expected[0].__name__, expected[1]))
    print("Found diffs:")
    for change_cls, change_str in hashed_changes:
        print('{}("{}"),'.format(change_cls.__name__, change_str))

    assert expected in hashed_changes


@pytest.mark.parametrize(
    "old_schema, new_schema, expected",
    # Isolate each test case.
    [
        pytest.param(
            old_schema, new_schema, change, id="{}:{}".format(group, change[1])
        )
        for group, old_schema, new_schema, changes in GROUPED_TEST_CASES
        for change in changes  # type: ignore
    ],
)
def test_diffs(old_schema, new_schema, expected):
    assert_change_found(list(diff_schema(old_schema, new_schema)), expected)


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
    changes = list(
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

    assert len(changes) == 1
    assert_change_found(changes, (TypeRemoved, "Type Type1 was removed."))
