# -*- coding: utf-8 -*-

import pytest

from py_gql._string_utils import dedent
from py_gql._utils import flatten
from py_gql.builders import SchemaDirective, build_schema
from py_gql.exc import SDLError
from py_gql.lang import ast as _ast
from py_gql.schema import (
    ID,
    UUID,
    Boolean,
    Field,
    Float,
    Int,
    ObjectType,
    String,
)


def test_object_type_extension():
    assert (
        build_schema(
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
        ).to_string()
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


def test_injected_object_type_extension():
    Foo = ObjectType("Foo", [Field("one", String)])
    schema = build_schema(
        """
        type Query {
            foo: Foo
        }

        extend type Foo {
            two: Int
        }
        """,
        additional_types=[Foo],
    )
    assert schema.to_string() == dedent(
        """
        type Foo {
            one: String
            two: Int
        }

        type Query {
            foo: Foo
        }
        """
    )

    assert schema.types["Foo"] is not Foo


def test_object_type_extension_duplicate_field():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query { foo: String }
            type Object { one: String }
            extend type Object { one: Int }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 34, "line": 4}],
        "message": 'Found duplicate field "one" when extending type "Object"',
    }


def test_object_type_extension_already_implemented_interface():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query { foo: String }
            interface IFace1 { one: String }
            type Object implements IFace1 { one: String }
            extend type Object implements IFace1
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 43, "line": 5}],
        "message": 'Interface "IFace1" already implemented for type "Object"',
    }


def test_object_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query { foo: String }
            type Object { one: String }
            extend input Object { two: Int }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 4}],
        "message": (
            "Expected ObjectTypeExtension when extending ObjectType "
            "but got InputObjectTypeExtension"
        ),
    }


def test_interface_type_extension():
    assert (
        build_schema(
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
        ).to_string()
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
        build_schema(
            """
            type Query { foo: IFace }
            interface IFace { one: String }
            extend interface IFace { one: Int }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 38, "line": 4}],
        "message": 'Found duplicate field "one" when extending interface "IFace"',
    }


def test_interface_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query { foo: IFace }
            interface IFace { one: String }
            extend type IFace { one: Int }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 4}],
        "message": (
            "Expected InterfaceTypeExtension when extending InterfaceType "
            "but got ObjectTypeExtension"
        ),
    }


def test_enum_extension():
    assert (
        build_schema(
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
        ).to_string()
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
        build_schema(
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

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 17, "line": 13}],
        "message": 'Found duplicate enum value "RED" when extending EnumType "Foo"',
    }


def test_enum_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
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

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 12}],
        "message": "Expected EnumTypeExtension when extending EnumType but got "
        "ObjectTypeExtension",
    }


def test_input_object_type_extension():
    assert (
        build_schema(
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
        ).to_string()
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
        build_schema(
            """
            type Query { foo(in: Foo): String }
            input Foo { one: Int }
            extend input Foo { one: Int }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 32, "line": 4}],
        "message": 'Found duplicate field "one" when extending input object "Foo"',
    }


def test_input_object_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query { foo(in: Foo): String }
            input Foo { one: Int }
            extend type Foo { two: Int }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 4}],
        "message": (
            "Expected InputObjectTypeExtension when extending InputObjectType "
            "but got ObjectTypeExtension"
        ),
    }


def test_union_type_extension():
    assert (
        build_schema(
            """
            type Query {
                foo: Foo
            }

            type Bar {
                bar: Int
            }

            type Baz {
                baz: Int
            }

            union Foo = Bar

            extend union Foo = Baz
            """
        ).to_string()
        == dedent(
            """
            type Bar {
                bar: Int
            }

            type Baz {
                baz: Int
            }

            union Foo = Bar | Baz

            type Query {
                foo: Foo
            }
            """
        )
    )


def test_union_type_extension_duplicate_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query {
                foo: Foo
            }

            type Bar {
                bar: Int
            }

            type Baz {
                baz: Int
            }

            union Foo = Bar

            extend union Foo = Bar
            """
        )

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 32, "line": 16}],
        "message": (
            'Found duplicate member type "Bar" when extending UnionType "Foo"'
        ),
    }


def test_union_type_extension_bad_extension():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query {
                foo: Foo
            }

            type Bar {
                bar: Int
            }

            type Baz {
                baz: Int
            }

            union Foo = Bar

            extend type Foo {
                one: Int
            }
            """
        )

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 16}],
        "message": (
            "Expected UnionTypeExtension when extending UnionType "
            "but got ObjectTypeExtension"
        ),
    }


def test_scalar_type_extension():
    class ProtectedDirective(SchemaDirective):
        def visit_scalar(self, scalar_type):
            return scalar_type

    schema = build_schema(
        """
        directive @protected on SCALAR

        type Query {
            foo: Foo
        }

        scalar Foo

        extend scalar Foo @protected
        """,
        schema_directives={"protected": ProtectedDirective},
    )

    assert schema.to_string() == dedent(
        """
        directive @protected on SCALAR

        scalar Foo

        type Query {
            foo: Foo
        }
        """
    )

    assert list(
        flatten(n.directives for n in schema.types["Foo"].nodes)  # type: ignore
    ) == [
        _ast.Directive(
            loc=(140, 150),
            name=_ast.Name(loc=(141, 150), value="protected"),
            arguments=[],
        )
    ]


def test_injected_scalar_type_extension():
    class ProtectedDirective(SchemaDirective):
        def visit_scalar(self, scalar_type):
            return scalar_type

    schema = build_schema(
        """
        directive @protected on SCALAR

        type Query {
            foo: UUID
        }

        extend scalar UUID @protected
        """,
        additional_types=[UUID],
        schema_directives={"protected": ProtectedDirective},
    )

    assert schema.to_string(include_descriptions=False) == dedent(
        """
        directive @protected on SCALAR

        type Query {
            foo: UUID
        }

        scalar UUID
        """
    )

    assert list(
        flatten(
            n.directives for n in schema.types["UUID"].nodes  # type: ignore
        )
    ) == [
        _ast.Directive(
            loc=(122, 132),
            name=_ast.Name(loc=(123, 132), value="protected"),
            arguments=[],
        )
    ]

    assert schema.types["UUID"] is not UUID


def test_does_not_extend_specified_scalar():
    schema = build_schema(
        """
        directive @protected on SCALAR

        type Query {
            foo: String
        }

        extend scalar String @protected
        extend scalar Int @protected
        extend scalar ID @protected
        extend scalar Boolean @protected
        extend scalar Float @protected
        """
    )

    assert schema.get_type("String") is String
    assert schema.get_type("Int") is Int
    assert schema.get_type("ID") is ID
    assert schema.get_type("Boolean") is Boolean
    assert schema.get_type("Float") is Float


def test_schema_extension():
    schema = build_schema(
        """
        type Query { a: Boolean }

        type Foo { foo: String }
        type Bar { bar: String }

        extend schema {
            mutation: Bar
        }
        """
    )

    assert schema.query_type.name == "Query"  # type: ignore
    assert schema.mutation_type.name == "Bar"  # type: ignore
    assert schema.subscription_type is None


def test_schema_extension_directive():
    build_schema(
        """
        directive @onSchema on SCHEMA

        type Foo { foo: String }
        type Bar { bar: String }

        schema {
            query: Foo
        }

        extend schema @onSchema
        """
    )


def test_mixed_definition_and_extension():
    assert (
        build_schema(
            """
            type Query { _noop: Int }

            interface Object {
                id: Int!
            }

            scalar Email

            extend type Query {
                employee(email: Email!): Employee
            }

            type Employee implements Object {
                id: Int!
                email: Email!
                active: Boolean!
            }
            """
        ).to_string()
        == dedent(
            """
            scalar Email

            type Employee implements Object {
                id: Int!
                email: Email!
                active: Boolean!
            }

            interface Object {
                id: Int!
            }

            type Query {
                _noop: Int
                employee(email: Email!): Employee
            }
            """
        )
    )
