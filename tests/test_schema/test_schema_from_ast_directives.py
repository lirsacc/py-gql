# -*- coding: utf-8 -*-

import hashlib

import pytest

from py_gql import graphql
from py_gql._string_utils import parse_block_string
from py_gql.exc import ScalarParsingError, SDLError
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
    print_schema,
    schema_from_ast,
)
from py_gql.schema.schema_directive import SchemaDirective, wrap_resolver

dedent = lambda s: parse_block_string(s, strip_trailing_newlines=False)


def test_simple_field_modifier():
    class UppercaseDirective(SchemaDirective):
        def visit_field(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x.upper())

    assert (
        graphql(
            schema_from_ast(
                """
                directive @upper on FIELD_DEFINITION

                type Query {
                    foo: String @upper
                }
                """,
                schema_directives={"upper": UppercaseDirective},
            ),
            "{ foo }",
            {},
            initial_value={"foo": "lowerCase"},
        ).response()
        == {"data": {"foo": "LOWERCASE"}}
    )


def test_directive_on_wrong_location():
    class UppercaseDirective(SchemaDirective):
        def visit_field(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x.upper())

    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            directive @upper on FIELD_DEFINITION

            type Query @upper {
                foo: String
            }
            """,
            schema_directives={"upper": UppercaseDirective},
        )

    assert exc_info.value.to_json() == {
        "locations": [{"column": 24, "line": 4}],
        "message": 'Directive "@upper" not applicable to "OBJECT"',
    }


def test_ignores_unknown_directive_implementation():
    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            directive @upper on FIELD_DEFINITION

            type Query @upper {
                foo: String
            }
            """
        )

    assert exc_info.value.to_json() == {
        "message": 'Missing directive implementation for "@upper"'
    }


def test_field_modifier_using_arguments():
    class PowerDirective(SchemaDirective):

        definition = Directive(
            "power",
            ["FIELD_DEFINITION"],
            [Argument("exponent", Int, default_value=2)],
        )

        def __init__(self, args):
            self.exponent = args["exponent"]

        def visit_field(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x ** self.exponent)

    assert (
        graphql(
            schema_from_ast(
                """
                type Query {
                    foo: Int @power
                    bar: Int @power(exponent: 3)
                }
                """,
                schema_directives={"power": PowerDirective},
            ),
            "{ foo, bar }",
            {},
            initial_value={"foo": 2, "bar": 2},
        ).response()
        == {"data": {"foo": 4, "bar": 8}}
    )


def test_object_modifier_and_field_modifier():
    class UppercaseDirective(SchemaDirective):
        def visit_field(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x.upper())

    class UniqueID(SchemaDirective):
        def __init__(self, args):
            self.name = args["name"]
            self.source = args["source"]
            assert len(self.source)

        def resolve(self, root, *args):
            m = hashlib.sha256()
            for fieldname in self.source:
                print(fieldname)
                m.update(str(root.get(fieldname, "")).encode("utf8"))
            return m.hexdigest()

        def visit_object(self, object_definition):
            assert self.name not in object_definition.field_map
            assert all(s in object_definition.field_map for s in self.source)
            return ObjectType(
                name=object_definition.name,
                description=object_definition.description,
                fields=(
                    [Field(self.name, String, resolve=self.resolve)]
                    + object_definition.fields
                ),
                interfaces=object_definition.interfaces,
                is_type_of=object_definition.is_type_of,
                nodes=object_definition.nodes,
            )

    schema = schema_from_ast(
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

    assert print_schema(schema, indent="    ") == dedent(
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

    assert graphql(
        schema,
        "{ foo { uid, name, id } }",
        {},
        initial_value={"foo": {"name": "some lower case name", "id": 42}},
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


def test_location_not_supported():
    class NoopDirective(SchemaDirective):
        pass

    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            directive @upper on FIELD_DEFINITION
            type Query {
                foo: String @upper
            }
            """,
            schema_directives={"upper": NoopDirective},
        )

    assert exc_info.value.to_json() == {
        "message": (
            "SchemaDirective implementation for @upper must "
            "support FIELD_DEFINITION"
        )
    }


def test_location_not_supported_2():
    class NoopDirective(SchemaDirective):
        pass

    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            directive @upper on SCHEMA

            schema @upper {
                query: Query
            }

            type Query {
                foo: String
            }
            """,
            schema_directives={"upper": NoopDirective},
        )

    assert exc_info.value.to_json() == {
        "message": (
            "SchemaDirective implementation for @upper must support SCHEMA"
        )
    }


def test_missing_definition():
    class NoopDirective(SchemaDirective):
        pass

    with pytest.raises(SDLError) as exc_info:
        schema_from_ast(
            """
            type Query {
                foo: String @upper
            }
            """,
            schema_directives={"upper": NoopDirective},
        )

    assert exc_info.value.to_json() == {
        "locations": [{"column": 29, "line": 3}],
        "message": 'Unknown directive "@upper',
    }


def test_multiple_directives_applied_in_order():
    class PowerDirective(SchemaDirective):

        definition = Directive(
            "power",
            ["FIELD_DEFINITION"],
            [Argument("exponent", Int, default_value=2)],
        )

        def __init__(self, args):
            self.exponent = args["exponent"]

        def visit_field(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x ** self.exponent)

    class PlusOneDirective(SchemaDirective):
        definition = Directive("plus_one", ["FIELD_DEFINITION"])

        def visit_field(self, field_definition):
            return wrap_resolver(field_definition, lambda x: x + 1)

    assert (
        graphql(
            schema_from_ast(
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
            {},
            initial_value={"foo": 2, "bar": 2},
        ).response()
        == {"data": {"foo": 5, "bar": 9}}
    )


def test_input_values():
    class LimitedLengthScalarType(ScalarType):
        @classmethod
        def wrap(cls, typ, *args, **kwargs):
            if isinstance(typ, (NonNullType, ListType)):
                return type(typ)(cls.wrap(typ.type, *args, **kwargs))
            return cls(typ, *args, **kwargs)

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

        def parse_literal(self, node, variables=None):
            return self.parse(node.value)

    class LimitedLengthDirective(SchemaDirective):
        def __init__(self, args):
            self.min = args["min"]
            self.max = args.get("max")

        definition = Directive(
            "len",
            ["ARGUMENT_DEFINITION", "INPUT_FIELD_DEFINITION"],
            [Argument("min", Int, default_value=0), Argument("max", Int)],
        )

        def visit_argument(self, arg):
            arg.type = LimitedLengthScalarType.wrap(
                arg.type, self.min, self.max
            )
            return arg

        def visit_input_field(self, field):
            field.type = LimitedLengthScalarType.wrap(
                field.type, self.min, self.max
            )
            return field

    schema = schema_from_ast(
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

    assert print_schema(schema, indent="    ") == dedent(
        """
        input BarInput {
            baz: LimitedLenthString_3_inf
        }

        type Query {
            foo(bar: BarInput, foo: LimitedLenthString_0_4): String
        }
        """
    )

    assert graphql(
        schema,
        '{ foo (foo: "abcdef") }',
        {},
        initial_value={"foo": lambda _, args, *r: args["foo"]},
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

    assert graphql(
        schema,
        '{ foo (foo: "abcd") }',
        {},
        initial_value={"foo": lambda _, args, *r: args["foo"]},
    ).response() == {"data": {"foo": "abcd"}}

    assert graphql(
        schema,
        '{ foo (bar: {baz: "abcd"}) }',
        {},
        initial_value={"foo": lambda _, args, *r: args["bar"]["baz"]},
    ).response() == {"data": {"foo": "abcd"}}

    assert graphql(
        schema,
        '{ foo (bar: {baz: "a"}) }',
        {},
        initial_value={"foo": lambda _, args, *r: args["bar"]["baz"]},
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
    VALUES = dict(
        [("RED", "#FF4136"), ("BLUE", "#0074D9"), ("GREEN", "#2ECC40")]
    )

    class CSSColorDirective(SchemaDirective):
        def visit_enum_value(self, enum_value):
            return EnumValue(
                enum_value.name,
                VALUES[enum_value.name],
                description=enum_value.description,
                deprecation_reason=enum_value.deprecation_reason,
            )

    schema = schema_from_ast(
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

    enum = schema.get_type("Color")
    for k, v in VALUES.items():
        assert enum.get_value(k) == v
        assert enum.get_name(v) == k


def test_enum_type_directive():
    """ generating custom enums """

    # These could be pre-loaded from a database or a config file dynamically
    VALUES = dict(
        [("RED", "#FF4136"), ("BLUE", "#0074D9"), ("GREEN", "#2ECC40")]
    )

    class GeneratedEnum(SchemaDirective):
        def visit_enum(self, enum):
            return EnumType(
                enum.name,
                VALUES.items(),
                description=enum.description,
                nodes=enum.nodes,
            )

    schema = schema_from_ast(
        """
        directive @generated on ENUM

        type Query {
            color: Color
        }

        enum Color @generated { _empty }
        """,
        schema_directives={"generated": GeneratedEnum},
    )

    assert print_schema(schema, indent="    ") == dedent(
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

    enum = schema.get_type("Color")
    for k, v in VALUES.items():
        assert enum.get_value(k) == v
        assert enum.get_name(v) == k
