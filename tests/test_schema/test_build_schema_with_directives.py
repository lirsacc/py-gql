# -*- coding: utf-8 -*-

import functools as ft
import hashlib
from typing import Any, cast

import pytest

from py_gql import graphql_blocking
from py_gql._string_utils import dedent
from py_gql.builders import (
    DeprecatedSchemaDirective,
    SchemaDirective,
    build_schema,
)
from py_gql.exc import ScalarParsingError, SDLError
from py_gql.execution import default_resolver
from py_gql.schema import (
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    String,
)


def wrap_resolver(field_def, func):
    source_resolver = field_def.resolver or default_resolver

    @ft.wraps(source_resolver)
    def wrapped(parent_value, context, info, **args):
        value = source_resolver(parent_value, context, info, **args)
        if value is None:
            return value
        return func(value)

    return Field(
        name=field_def.name,
        type_=field_def.type,
        description=field_def.description,
        deprecation_reason=field_def.deprecation_reason,
        args=field_def.arguments,
        resolver=wrapped,
        node=field_def.node,
    )


def test_simple_field_modifier():
    class UppercaseDirective(SchemaDirective):
        def on_field_definition(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x.upper())

    assert (
        graphql_blocking(
            build_schema(
                """
                directive @upper on FIELD_DEFINITION

                type Query {
                    foo: String @upper
                }
                """,
                schema_directives={"upper": UppercaseDirective},
            ),
            "{ foo }",
            root={"foo": "lowerCase"},
        ).response()
        == {"data": {"foo": "LOWERCASE"}}
    )


def test_directive_on_wrong_location():
    class UppercaseDirective(SchemaDirective):
        def on_field_definition(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x.upper())

    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            directive @upper on FIELD_DEFINITION

            type Query @upper {
                foo: String
            }
            """,
            schema_directives={"upper": UppercaseDirective},
        )

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 24, "line": 4}],
        "message": 'Directive "@upper" not applicable to "OBJECT"',
    }


def test_ignores_unknown_directive_implementation():
    build_schema(
        """
        directive @upper on FIELD_DEFINITION

        type Query @upper {
            foo: String
        }
        """
    )


def test_field_modifier_using_arguments():
    class PowerDirective(SchemaDirective):

        definition = Directive(
            "power",
            ["FIELD_DEFINITION"],
            args=[Argument("exponent", Int, default_value=2)],
        )

        # pylint: disable = super-init-not-called
        def __init__(self, args):
            self.exponent = args["exponent"]

        def on_field_definition(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x ** self.exponent)

    assert (
        graphql_blocking(
            build_schema(
                """
                type Query {
                    foo: Int @power
                    bar: Int @power(exponent: 3)
                }
                """,
                schema_directives={"power": PowerDirective},
            ),
            "{ foo, bar }",
            root={"foo": 2, "bar": 2},
        ).response()
        == {"data": {"foo": 4, "bar": 8}}
    )


def test_object_modifier_and_field_modifier():
    class UppercaseDirective(SchemaDirective):
        def on_field_definition(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x.upper())

    class UniqueID(SchemaDirective):
        # pylint:disable=super-init-not-called
        def __init__(self, args):
            self.name = args["name"]
            self.source = args["source"]
            assert len(self.source)

        def resolve(self, root, *_, **args):
            m = hashlib.sha256()
            for fieldname in self.source:
                m.update(str(root.get(fieldname, "")).encode("utf8"))
            return m.hexdigest()

        def on_object(self, object_definition):
            assert self.name not in object_definition.field_map
            assert all(s in object_definition.field_map for s in self.source)
            return ObjectType(
                name=object_definition.name,
                description=object_definition.description,
                fields=(
                    [Field(self.name, String, resolver=self.resolve)]
                    + object_definition.fields
                ),
                interfaces=object_definition.interfaces,
                is_type_of=object_definition.is_type_of,
                nodes=object_definition.nodes,
            )

    schema = build_schema(
        """
        directive @uid (name: String! = "uid", source: [String]!) on OBJECT
        directive @upper on FIELD_DEFINITION

        type Query {
            foo: Foo
        }

        type Foo @uid (source: ["id", "name"]) {
            id: Int
            name: String @upper
        }
        """,
        schema_directives={"upper": UppercaseDirective, "uid": UniqueID},
    )

    assert schema.to_string() == dedent(
        """
        directive @uid(name: String! = "uid", source: [String]!) on OBJECT

        directive @upper on FIELD_DEFINITION

        type Foo {
            uid: String
            id: Int
            name: String
        }

        type Query {
            foo: Foo
        }
        """
    )

    assert graphql_blocking(
        schema,
        "{ foo { uid, name, id } }",
        root={"foo": {"name": "some lower case name", "id": 42}},
    ).response() == {
        "data": {
            "foo": {
                "uid": (
                    "6dc146d52a9962cfb9b29c2414f68cc628e2a0dcce"
                    "7832760ddf39a441726173"
                ),
                "name": "SOME LOWER CASE NAME",
                "id": 42,
            }
        }
    }


def test_missing_definition():
    class NoopDirective(SchemaDirective):
        pass

    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query {
                foo: String @upper
            }
            """,
            schema_directives={"upper": NoopDirective},
        )

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 29, "line": 3}],
        "message": 'Unknown directive "@upper',
    }


def test_multiple_directives_applied_in_order():
    class PowerDirective(SchemaDirective):

        definition = Directive(
            "power",
            ["FIELD_DEFINITION"],
            args=[Argument("exponent", Int, default_value=2)],
        )

        # pylint:disable=super-init-not-called
        def __init__(self, args):
            self.exponent = args["exponent"]

        def on_field_definition(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x ** self.exponent)

    class PlusOneDirective(SchemaDirective):
        definition = Directive("plus_one", ["FIELD_DEFINITION"])

        def on_field_definition(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x + 1)

    assert (
        graphql_blocking(
            build_schema(
                """
                type Query {
                    foo: Int @power @plus_one
                    bar: Int @plus_one @power
                }
                """,
                schema_directives={
                    "power": PowerDirective,
                    "plus_one": PlusOneDirective,
                },
            ),
            "{ foo, bar }",
            root={"foo": 2, "bar": 2},
        ).response()
        == {"data": {"foo": 5, "bar": 9}}
    )


def test_input_values():
    class LimitedLengthScalarType(ScalarType):
        @classmethod
        def wrap(
            cls, type_: ScalarType, *args: Any, **kwargs: Any
        ) -> "LimitedLengthScalarType":
            if isinstance(type_, (NonNullType, ListType)):
                return type(type_)(cls.wrap(type_.type, *args, **kwargs))
            return cls(type_, *args, **kwargs)

        # pylint:disable=super-init-not-called,redefined-builtin
        def __init__(self, type, min, max):
            assert isinstance(type, ScalarType)
            self.type = type
            self.min = min
            self.max = max if max is not None else float("inf")
            assert self.min >= 0
            assert self.max >= 0
            self.name = "LimitedLenth%s_%s_%s" % (type.name, self.min, self.max)

        def serialize(self, value):
            return self.type.serialize(value)

        def parse(self, value):
            parsed = self.type.parse(value)
            if not isinstance(parsed, str):
                raise ScalarParsingError("Not a string")
            if not (self.min <= len(parsed) <= self.max):
                raise ScalarParsingError(
                    "%s length must be between %s and %s but was %s"
                    % (self.name, self.min, self.max, len(parsed))
                )
            return parsed

    class LimitedLengthDirective(SchemaDirective):

        # pylint:disable=super-init-not-called
        def __init__(self, args):
            self.min = args["min"]
            self.max = args.get("max")

        definition = Directive(
            "len",
            ["ARGUMENT_DEFINITION", "INPUT_FIELD_DEFINITION"],
            [Argument("min", Int, default_value=0), Argument("max", Int)],
        )

        def on_argument_definition(self, arg):
            arg.type = LimitedLengthScalarType.wrap(
                arg.type, self.min, self.max
            )
            return arg

        def on_input_field_definition(self, field):
            field.type = LimitedLengthScalarType.wrap(
                field.type, self.min, self.max
            )
            return field

    schema = build_schema(
        """
        type Query {
            foo (
                bar: BarInput
                foo: String @len(max: 4)
            ): String
        }

        input BarInput {
            baz: String @len(min: 3)
        }
        """,
        schema_directives={"len": LimitedLengthDirective},
    )

    assert schema.to_string() == dedent(
        """
        input BarInput {
            baz: LimitedLenthString_3_inf
        }

        type Query {
            foo(bar: BarInput, foo: LimitedLenthString_0_4): String
        }
        """
    )

    assert graphql_blocking(
        schema,
        '{ foo (foo: "abcdef") }',
        root={"foo": lambda *_, **args: args["foo"]},
    ).response() == {
        "errors": [
            {
                "locations": [{"column": 13, "line": 1}],
                "message": (
                    "Expected type LimitedLenthString_0_4, found "
                    '"abcdef" (LimitedLenthString_0_4 length must be '
                    "between 0 and 4 but was 6)"
                ),
            }
        ]
    }

    assert graphql_blocking(
        schema,
        '{ foo (foo: "abcd") }',
        root={"foo": lambda *_, **args: args["foo"]},
    ).response() == {"data": {"foo": "abcd"}}

    assert graphql_blocking(
        schema,
        '{ foo (bar: {baz: "abcd"}) }',
        root={"foo": lambda *_, **args: args["bar"]["baz"]},
    ).response() == {"data": {"foo": "abcd"}}

    assert graphql_blocking(
        schema,
        '{ foo (bar: {baz: "a"}) }',
        root={"foo": lambda *_, **args: args["bar"]["baz"]},
    ).response() == {
        "errors": [
            {
                "locations": [{"column": 19, "line": 1}],
                "message": (
                    'Expected type LimitedLenthString_3_inf, found "a" '
                    "(LimitedLenthString_3_inf length must be between 3 "
                    "and inf but was 1)"
                ),
            }
        ]
    }


def test_enum_value_directive():
    """ generating custom enum values """

    # These could be pre-loaded from a database or a config file dynamically
    VALUES = {"RED": "#FF4136", "BLUE": "#0074D9", "GREEN": "#2ECC40"}

    class CSSColorDirective(SchemaDirective):
        def on_enum_value(self, enum_value):
            return EnumValue(
                enum_value.name,
                VALUES[enum_value.name],
                description=enum_value.description,
                deprecation_reason=enum_value.deprecation_reason,
            )

    schema = build_schema(
        """
        directive @cssColor on ENUM_VALUE

        type Query {
            color: Color
        }

        enum Color {
            RED @cssColor
            BLUE @cssColor
            GREEN @cssColor
        }
        """,
        schema_directives={"cssColor": CSSColorDirective},
    )

    enum = cast(EnumType, schema.get_type("Color"))
    for k, v in VALUES.items():
        assert enum.get_value(k) == v
        assert enum.get_name(v) == k


def test_enum_type_directive():
    """ generating custom enums """

    # These could be pre-loaded from a database or a config file dynamically
    VALUES = [("RED", "#FF4136"), ("BLUE", "#0074D9"), ("GREEN", "#2ECC40")]

    class GeneratedEnum(SchemaDirective):
        def on_enum(self, enum):
            return EnumType(
                enum.name,
                VALUES,
                description=enum.description,
                nodes=enum.nodes,
            )

    schema = build_schema(
        """
        directive @generated on ENUM

        type Query {
            color: Color
        }

        enum Color @generated { _empty }
        """,
        schema_directives={"generated": GeneratedEnum},
    )

    assert schema.to_string() == dedent(
        """
        directive @generated on ENUM

        enum Color {
            RED
            BLUE
            GREEN
        }

        type Query {
            color: Color
        }
        """
    )

    enum = cast(EnumType, schema.get_type("Color"))
    values_dict = dict(VALUES)
    for k, v in values_dict.items():
        assert enum.get_value(k) == v
        assert enum.get_name(v) == k


def test_schema_extension_duplicate_directive():
    class OnSchema(SchemaDirective):
        def on_schema(self, schema):
            pass

    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            directive @onSchema on SCHEMA

            type Foo { foo: String }
            type Bar { bar: String }

            schema @onSchema {
                query: Foo
            }

            extend schema @onSchema
            """,
            schema_directives={"onSchema": OnSchema},
        )

    assert exc_info.value.to_dict() == {
        "locations": [{"column": 27, "line": 11}],
        "message": 'Directive "@onSchema" already applied',
    }


class TestDeprecatedSchemaDirective:

    sdl = """
    type Query {
        foo: Foo
    }

    type Foo {
        a: Int
        b: Int @deprecated
        c: Bar
    }

    enum Bar {
        A
        B @deprecated(reason: "I don't like b")
        C
    }
    """

    def test_marks_field_as_deprecated_with_default_reason(self):
        schema = build_schema(
            self.sdl,
            schema_directives={"deprecated": DeprecatedSchemaDirective},
        )
        foo_type = schema.get_type("Foo")
        b_field = cast(ObjectType, foo_type).field_map["b"]
        assert b_field.deprecated
        assert b_field.deprecation_reason

    def test_marks_enum_value_as_deprecated_with_custom_reason(self):
        schema = build_schema(
            self.sdl,
            schema_directives={"deprecated": DeprecatedSchemaDirective},
        )
        bar_type = schema.get_type("Bar")
        b_value = cast(EnumType, bar_type)._values["B"]
        assert b_value.deprecated
        assert b_value.deprecation_reason == "I don't like b"
