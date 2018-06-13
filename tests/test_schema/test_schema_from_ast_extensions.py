# -*- coding: utf-8 -*-

import pytest

from py_gql.exc import SDLError
from py_gql._string_utils import parse_block_string
from py_gql.schema import print_schema, schema_from_ast

dedent = lambda s: parse_block_string(s, strip_trailing_newlines=False)


def test_object_type_extension():
    assert (
        print_schema(
            schema_from_ast(
                """
                type Query {
                    foo: Object
                }

                interface IFace1 {
                    one: String
                }

                type Object implements IFace1 {
                    one: String
                    two: Int
                }

                interface IFace2 {
                    three: String
                }

                extend type Object implements IFace2 {
                    three: String
                }
                """
            ),
            indent="    ",
        )
        == dedent(
            """
            interface IFace1 {
                one: String
            }

            interface IFace2 {
                three: String
            }

            type Object implements IFace1 & IFace2 {
                one: String
                two: Int
                three: String
            }

            type Query {
                foo: Object
            }
            """
        )
    )


def test_object_type_extension_duplicate_field():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo: String }
            type Object { one: String }
            extend type Object { one: Int }
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 34, "line": 4}],
        "message": 'Duplicate field "one" when extending type "Object"',
    }


def test_object_type_extension_already_implemented_interface():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo: String }
            interface IFace1 { one: String }
            type Object implements IFace1 { one: String }
            extend type Object implements IFace1
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 43, "line": 5}],
        "message": 'Interface "IFace1" already implemented for type "Object"',
    }


def test_object_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo: String }
            type Object { one: String }
            extend input Object { two: Int }
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 13, "line": 3}],
        "message": (
            "Expected an ObjectTypeExtension node for ObjectType "
            '"Object" but got InputObjectTypeExtension'
        ),
    }


def test_interface_type_extension():
    assert (
        print_schema(
            schema_from_ast(
                """
                type Query {
                    foo: IFace
                }

                interface IFace {
                    one: String
                }

                extend interface IFace {
                    two: String
                }
                """
            ),
            indent="    ",
        )
        == dedent(
            """
            interface IFace {
                one: String
                two: String
            }

            type Query {
                foo: IFace
            }
            """
        )
    )


def test_interface_type_extension_duplicate_field():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo: IFace }
            interface IFace { one: String }
            extend interface IFace { one: Int }
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 38, "line": 4}],
        "message": 'Duplicate field "one" when extending interface "IFace"',
    }


def test_interface_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo: IFace }
            interface IFace { one: String }
            extend type IFace { one: Int }
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 13, "line": 3}],
        "message": (
            "Expected an InterfaceTypeExtension node for InterfaceType "
            '"IFace" but got ObjectTypeExtension'
        ),
    }


def test_enum_extension():
    assert (
        print_schema(
            schema_from_ast(
                """
                type Query {
                    foo: Foo
                }

                enum Foo {
                    BLUE
                    GREEN
                    RED
                }

                extend enum Foo {
                    YELLOW
                }
                """
            ),
            indent="    ",
        )
        == dedent(
            """
            enum Foo {
                BLUE
                GREEN
                RED
                YELLOW
            }

            type Query {
                foo: Foo
            }
            """
        )
    )


def test_enum_extension_duplicate_value():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query {
                foo: Foo
            }

            enum Foo {
                BLUE
                GREEN
                RED
            }

            extend enum Foo {
                RED
            }
            """
        )

    assert exc_info.value.to_json() == {
        "locations": [{"column": 17, "line": 13}],
        "message": 'Duplicate enum value "RED" when extending EnumType "Foo"',
    }


def test_enum_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query {
                foo: Foo
            }

            enum Foo {
                BLUE
                GREEN
                RED
            }

            extend type Foo {
                one: Int
            }
            """
        )

    assert exc_info.value.to_json() == {
        "locations": [{"column": 13, "line": 6}],
        "message": 'Expected an EnumTypeExtension node for EnumType "Foo" but got '
        "ObjectTypeExtension",
    }


def test_input_object_type_extension():
    assert (
        print_schema(
            schema_from_ast(
                """
                type Query {
                    foo(in: Foo): String
                }

                input Foo {
                    one: Int
                }

                extend input Foo {
                    two: String
                }
                """
            ),
            indent="    ",
        )
        == dedent(
            """
            input Foo {
                one: Int
                two: String
            }

            type Query {
                foo(in: Foo): String
            }
            """
        )
    )


def test_input_object_type_extension_duplicate_field():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo(in: Foo): String }
            input Foo { one: Int }
            extend input Foo { one: Int }
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 32, "line": 4}],
        "message": 'Duplicate field "one" when extending input object "Foo"',
    }


def test_input_object_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query { foo(in: Foo): String }
            input Foo { one: Int }
            extend type Foo { two: Int }
            """
        )
    assert exc_info.value.to_json() == {
        "locations": [{"column": 13, "line": 3}],
        "message": (
            "Expected an InputObjectTypeExtension node for InputObjectType "
            '"Foo" but got ObjectTypeExtension'
        ),
    }
