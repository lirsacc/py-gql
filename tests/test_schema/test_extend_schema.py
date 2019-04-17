# -*- coding: utf-8 -*-
""" Tests for extend schema from a pre-built schema. """
# This file only test some cases that are not exercised when testing
# build_schema as well as adds some lower level assertions.

from typing import cast

import pytest

from py_gql._string_utils import dedent
from py_gql.builders import build_schema_ignoring_extensions, extend_schema
from py_gql.exc import SDLError
from py_gql.lang import ast as _ast
from py_gql.schema import (
    Argument,
    Directive,
    Field,
    InputField,
    InputObjectType,
    Int,
    ObjectType,
    Schema,
)

BASE_SCHEMA = Schema(ObjectType("Query", [Field("foo", Int)]))


def test_noop_without_extension_nodes():
    # NOTE: The parser cannot technically build such a document
    new_schema = extend_schema(BASE_SCHEMA, _ast.Document(definitions=[]))
    assert new_schema is BASE_SCHEMA


def test_raises_on_schema_definition_in_strict_mode():
    with pytest.raises(SDLError):
        extend_schema(
            BASE_SCHEMA,
            """
            schema {
                query: Query
            }
            """,
        )


def test_raises_on_known_type_in_strict_mode():
    with pytest.raises(SDLError):
        extend_schema(BASE_SCHEMA, "scalar String")


def test_ignores_known_type_in_non_strict_mode():
    new_schema = extend_schema(BASE_SCHEMA, "scalar String", strict=False)
    assert new_schema is BASE_SCHEMA


def test_raises_on_known_directive_in_strict_mode():
    with pytest.raises(SDLError):
        extend_schema(
            BASE_SCHEMA,
            "directive @skip(if: Boolean!)"
            "on FIELD | FRAGMENT_SPREAD | INLINE_FRAGMENT",
        )


def test_ignores_known_directive_in_non_strict_mode():
    new_schema = extend_schema(
        BASE_SCHEMA,
        "directive @skip(if: Boolean!)"
        "on FIELD | FRAGMENT_SPREAD | INLINE_FRAGMENT",
        strict=False,
    )
    assert new_schema is BASE_SCHEMA


def test_ignore_errors_in_non_strict_mode():
    sdl = """
    directive @FooDirective (a: Int) on FIELD
    type FooType { a: String }
    type Query { foo: FooType! }
    extend type BarType { a: String }
    """
    extend_schema(build_schema_ignoring_extensions(sdl), sdl, strict=False)


def test_raises_on_unknown_type_in_strict_mode():
    with pytest.raises(SDLError):
        extend_schema(BASE_SCHEMA, "extend scalar UUID @foo")


def test_ignores_unknown_type_in_non_strict_mode():
    new_schema = extend_schema(
        BASE_SCHEMA, "extend scalar UUID @foo", strict=False
    )
    assert new_schema is BASE_SCHEMA


def test_it_adds_new_type_definitions_and_opeations_to_schema():
    assert (
        extend_schema(
            BASE_SCHEMA,
            """
            scalar UUID

            type SomeMutation {
                bar: UUID
            }

            extend schema {
                mutation: SomeMutation
            }
            """,
        ).to_string()
        == dedent(
            """
            schema {
                query: Query
                mutation: SomeMutation
            }

            type Query {
                foo: Int
            }

            type SomeMutation {
                bar: UUID
            }

            scalar UUID
            """
        )
    )


def test_it_rejects_duplicate_operation():
    with pytest.raises(SDLError):
        extend_schema(
            BASE_SCHEMA,
            """
            type NewQuery { bar: String }
            extend schema { query: NewQuery }
            """,
        )


def test_it_adds_new_directives_to_schema():
    assert extend_schema(
        BASE_SCHEMA, "directive @some(a: Boolean!) on FIELD"
    ).to_string() == dedent(
        """
        directive @some(a: Boolean!) on FIELD

        type Query {
            foo: Int
        }
        """
    )


def test_it_correctly_updates_references():
    arg_type = InputObjectType("Bar", [InputField("a", Int)])
    schema_with_args = Schema(
        query_type=ObjectType(
            "Query",
            [
                Field(
                    "foo",
                    ObjectType("Foo", [Field("a", Int)]),
                    [Argument("bar", arg_type)],
                )
            ],
        ),
        directives=[Directive("baz", ["FIELD"], [Argument("bar", arg_type)])],
    )

    update_schema = extend_schema(
        schema_with_args,
        """
        extend input Bar {
            b: String
        }

        extend type Foo {
            b: String
        }
        """,
    )

    assert update_schema.to_string() == dedent(
        """
        directive @baz(bar: Bar) on FIELD

        input Bar {
            a: Int
            b: String
        }

        type Foo {
            a: Int
            b: String
        }

        type Query {
            foo(bar: Bar): Foo
        }
        """
    )

    query_type = cast(ObjectType, update_schema.get_type("Query"))
    field_type = query_type.field_map["foo"].type
    root_field_type = update_schema.get_type("Foo")

    assert root_field_type is field_type

    field_arg_type = query_type.field_map["foo"].argument_map["bar"].type
    directive_arg_type = (
        cast(Directive, update_schema.directives.get("baz"))
        .argument_map["bar"]
        .type
    )
    root_arg_type = update_schema.get_type("Bar")

    assert field_arg_type is root_arg_type
    assert directive_arg_type is root_arg_type
