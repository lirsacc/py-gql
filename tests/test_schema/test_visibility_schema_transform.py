# -*- coding: utf-8 -*-

import pytest

from py_gql import build_schema
from py_gql._string_utils import dedent
from py_gql.schema.transforms import VisibilitySchemaTransform, transform_schema


@pytest.fixture
def schema():
    return build_schema(
        """
        directive @barDirective(arg: SomeEnum, other_arg: Int) on FIELD

        directive @fooDirective on FIELD

        type Bar implements IFace {
            name: String
        }

        type Foo implements IFace {
            name: String
        }

        interface IFace {
            name: String
        }

        type Query {
            a(arg: SomeEnum, other_arg: Int): String
            foo: Foo
            iface: IFace
            union: Thing
            uid: UUID
        }

        enum SomeEnum {
            FOO
            BAR
        }

        union Thing = Foo | Bar

        scalar UUID
        """
    )


def _hide_type_transform(target):
    class HideType(VisibilitySchemaTransform):
        def is_type_visible(self, name):
            return name != target

    return HideType()


def _sdl(s):
    return s.to_string(include_introspection=False, include_descriptions=False)


def test_hides_object(schema):
    assert (
        dedent(
            """
            directive @barDirective(arg: SomeEnum, other_arg: Int) on FIELD

            directive @fooDirective on FIELD

            type Bar implements IFace {
                name: String
            }

            interface IFace {
                name: String
            }

            type Query {
                a(arg: SomeEnum, other_arg: Int): String
                iface: IFace
                union: Thing
                uid: UUID
            }

            enum SomeEnum {
                FOO
                BAR
            }

            union Thing = Bar

            scalar UUID
            """
        )
        == _sdl(transform_schema(schema, _hide_type_transform("Foo")))
    )


def test_hides_interface(schema):
    assert (
        dedent(
            """
            directive @barDirective(arg: SomeEnum, other_arg: Int) on FIELD

            directive @fooDirective on FIELD

            type Bar {
                name: String
            }

            type Foo {
                name: String
            }

            type Query {
                a(arg: SomeEnum, other_arg: Int): String
                foo: Foo
                union: Thing
                uid: UUID
            }

            enum SomeEnum {
                FOO
                BAR
            }

            union Thing = Foo | Bar

            scalar UUID
            """
        )
        == _sdl(transform_schema(schema, _hide_type_transform("IFace")))
    )


def test_hides_union(schema):
    assert (
        dedent(
            """
            directive @barDirective(arg: SomeEnum, other_arg: Int) on FIELD

            directive @fooDirective on FIELD

            type Bar implements IFace {
                name: String
            }

            type Foo implements IFace {
                name: String
            }

            interface IFace {
                name: String
            }

            type Query {
                a(arg: SomeEnum, other_arg: Int): String
                foo: Foo
                iface: IFace
                uid: UUID
            }

            enum SomeEnum {
                FOO
                BAR
            }

            scalar UUID
            """
        )
        == _sdl(transform_schema(schema, _hide_type_transform("Thing")))
    )


def test_hides_enum(schema):
    assert (
        dedent(
            """
            directive @barDirective(other_arg: Int) on FIELD

            directive @fooDirective on FIELD

            type Bar implements IFace {
                name: String
            }

            type Foo implements IFace {
                name: String
            }

            interface IFace {
                name: String
            }

            type Query {
                a(other_arg: Int): String
                foo: Foo
                iface: IFace
                union: Thing
                uid: UUID
            }

            union Thing = Foo | Bar

            scalar UUID
            """
        )
        == _sdl(transform_schema(schema, _hide_type_transform("SomeEnum")))
    )


def test_hides_custom_scalar(schema):
    assert (
        dedent(
            """
            directive @barDirective(arg: SomeEnum, other_arg: Int) on FIELD

            directive @fooDirective on FIELD

            type Bar implements IFace {
                name: String
            }

            type Foo implements IFace {
                name: String
            }

            interface IFace {
                name: String
            }

            type Query {
                a(arg: SomeEnum, other_arg: Int): String
                foo: Foo
                iface: IFace
                union: Thing
            }

            enum SomeEnum {
                FOO
                BAR
            }

            union Thing = Foo | Bar
            """
        )
        == _sdl(transform_schema(schema, _hide_type_transform("UUID")))
    )


def test_does_not_hide_specified_scalar(schema):
    assert _sdl(schema) == _sdl(
        transform_schema(schema, _hide_type_transform("String"))
    )


def test_hides_directive(schema):
    class HideDirective(VisibilitySchemaTransform):
        def is_directive_visible(self, name):
            return name != "fooDirective"

    assert (
        dedent(
            """
            directive @barDirective(arg: SomeEnum, other_arg: Int) on FIELD

            type Bar implements IFace {
                name: String
            }

            type Foo implements IFace {
                name: String
            }

            interface IFace {
                name: String
            }

            type Query {
                a(arg: SomeEnum, other_arg: Int): String
                foo: Foo
                iface: IFace
                union: Thing
                uid: UUID
            }

            enum SomeEnum {
                FOO
                BAR
            }

            union Thing = Foo | Bar

            scalar UUID
            """
        )
        == _sdl(transform_schema(schema, HideDirective()))
    )


def test_hides_input_type_field():
    schema = build_schema(
        """
        input Foo {
            name: String
            id: ID!
        }

        input Bar {
            name: String
            id: ID!
        }

        type Query {
            field(foo: Foo, bar: Bar): String
        }
        """
    )

    class HideInputField(VisibilitySchemaTransform):
        def is_input_field_visible(self, typename, fieldname):
            return not (typename == "Foo" and fieldname == "name")

    assert (
        dedent(
            """
            input Bar {
                name: String
                id: ID!
            }

            input Foo {
                id: ID!
            }

            type Query {
                field(foo: Foo, bar: Bar): String
            }
            """
        )
        == _sdl(transform_schema(schema, HideInputField()))
    )
