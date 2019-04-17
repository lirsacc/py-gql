# -*- coding: utf-8 -*-

import pytest

from py_gql._string_utils import dedent
from py_gql.schema import (
    UUID,
    Argument,
    Directive,
    EnumType,
    Field,
    InputField,
    InputObjectType,
    Int,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    RegexType,
    Schema,
    String,
    UnionType,
)


def print_schema(schema, *args, **kwargs):
    return schema.to_string(*args, **kwargs)


def _single_field_schema(*args, **opts):
    return Schema(ObjectType("Query", [Field("singleField", *args, **opts)]))


def test_empty_schema():
    assert print_schema(Schema()) == ""


@pytest.mark.parametrize(
    "type_, opts, expected",
    [
        (String, {}, "String"),
        (ListType(String), {}, "[String]"),
        (NonNullType(String), {}, "String!"),
        (NonNullType(ListType(String)), {}, "[String]!"),
        (ListType(NonNullType(String)), {}, "[String!]"),
        (NonNullType(ListType(NonNullType(String))), {}, "[String!]!"),
    ],
)
def test_single_field_schema(type_, opts, expected):
    assert (
        dedent(
            """
            type Query {
                singleField: %s
            }
            """
            % expected
        )
        == print_schema(_single_field_schema(type_, **opts), indent="    ")
    )


def test_mutation():
    assert (
        dedent(
            """
            type Mutation {
                foo: Int
            }
            """
        )
        == print_schema(
            Schema(mutation_type=ObjectType("Mutation", [Field("foo", Int)]))
        )
    )


def test_custom_mutation():
    assert (
        dedent(
            """
            schema {
                mutation: CustomMutation
            }

            type CustomMutation {
                foo: Int
            }
            """
        )
        == print_schema(
            Schema(
                mutation_type=ObjectType("CustomMutation", [Field("foo", Int)])
            )
        )
    )


def test_subscription():
    assert (
        dedent(
            """
            type Subscription {
                foo: Int
            }
            """
        )
        == print_schema(
            Schema(
                subscription_type=ObjectType(
                    "Subscription", [Field("foo", Int)]
                )
            )
        )
    )


def test_custom_subscription():
    assert (
        dedent(
            """
            schema {
                subscription: CustomSubscription
            }

            type CustomSubscription {
                foo: Int
            }
            """
        )
        == print_schema(
            Schema(
                subscription_type=ObjectType(
                    "CustomSubscription", [Field("foo", Int)]
                )
            )
        )
    )


def test_object_field():
    schema = _single_field_schema(ObjectType("Foo", [Field("str", String)]))
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Foo {
            str: String
        }

        type Query {
            singleField: Foo
        }
        """
    )


def test_string_field_with_int_arg():
    schema = _single_field_schema(String, args=[Argument("argOne", Int)])
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: Int): String
        }
        """
    )


def test_string_field_with_int_arg_with_default_value():
    schema = _single_field_schema(
        String, args=[Argument("argOne", Int, default_value=2)]
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: Int = 2): String
        }
        """
    )


def test_string_field_with_string_arg_with_default_value():
    schema = _single_field_schema(
        String,
        args=[Argument("argOne", String, default_value="tes\t de\fault")],
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: String = "tes\\t de\\fault"): String
        }
        """
    )


def test_string_field_with_int_arg_with_null_default_value():
    schema = _single_field_schema(
        String, args=[Argument("argOne", Int, default_value=None)]
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: Int = null): String
        }
        """
    )


def test_string_field_with_non_null_int_arg():
    schema = _single_field_schema(
        String, args=[Argument("argOne", NonNullType(Int))]
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: Int!): String
        }
        """
    )


def test_string_field_with_multiple_args():
    schema = _single_field_schema(
        String, args=[Argument("argOne", Int), Argument("argTwo", String)]
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: Int, argTwo: String): String
        }
        """
    )


def test_string_field_with_multiple_args_with_default():
    schema = _single_field_schema(
        String,
        args=[
            Argument("argOne", Int, default_value=2),
            Argument("argTwo", String),
        ],
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        type Query {
            singleField(argOne: Int = 2, argTwo: String): String
        }
        """
    )


def test_custom_query_root_type():
    assert print_schema(
        Schema(ObjectType("CustomQueryType", [Field("foo", String)])),
        indent="    ",
    ) == dedent(
        """
        schema {
            query: CustomQueryType
        }

        type CustomQueryType {
            foo: String
        }
        """
    )


def test_interfaces():
    Foo = InterfaceType("Foo", [Field("str", String)])
    Baz = InterfaceType("Baz", [Field("int", Int)])
    Bar = ObjectType(
        "Bar", [Field("str", String), Field("int", Int)], interfaces=[Foo, Baz]
    )
    Query = ObjectType("Query", [Field("bar", Bar)])
    assert print_schema(Schema(Query), indent="    ") == dedent(
        """
        type Bar implements Foo & Baz {
            str: String
            int: Int
        }

        interface Baz {
            int: Int
        }

        interface Foo {
            str: String
        }

        type Query {
            bar: Bar
        }
        """
    )


def test_unions():
    Foo = ObjectType("Foo", [Field("str", String)])
    Bar = ObjectType("Bar", [Field("int", Int)])
    SingleUnion = UnionType("SingleUnion", types=[Foo])
    MultiUnion = UnionType("MultiUnion", types=[Foo, Bar])
    Query = ObjectType(
        "Query", [Field("single", SingleUnion), Field("multi", MultiUnion)]
    )
    assert print_schema(Schema(Query), indent="    ") == dedent(
        """
        type Bar {
            int: Int
        }

        type Foo {
            str: String
        }

        union MultiUnion = Foo | Bar

        type Query {
            single: SingleUnion
            multi: MultiUnion
        }

        union SingleUnion = Foo
        """
    )


def test_input_type():
    Input = InputObjectType("InputType", [InputField("int", Int)])
    Query = ObjectType(
        "Query", [Field("str", String, [Argument("argOne", Input)])]
    )
    assert print_schema(Schema(Query), indent="    ") == dedent(
        """
        input InputType {
            int: Int
        }

        type Query {
            str(argOne: InputType): String
        }
        """
    )


def test_custom_scalar_uuid():
    assert print_schema(_single_field_schema(UUID), indent="    ") == dedent(
        '''
        type Query {
            singleField: UUID
        }

        """
        The `UUID` scalar type represents a UUID as specified in [RFC 4122]\
[https://tools.ietf.org/html/rfc4122]
        """
        scalar UUID
        '''
    )


def test_custom_scalar_regex_type():
    assert print_schema(
        _single_field_schema(RegexType("BBQ", r"^BBQ$")), indent="    "
    ) == dedent(
        '''
        """String matching pattern /^BBQ$/"""
        scalar BBQ

        type Query {
            singleField: BBQ
        }
        '''
    )


def test_enum():
    Enum = EnumType("RGB", [("RED", 0), ("GREEN", 1), ("BLUE", 2)])
    assert print_schema(
        Schema(ObjectType("Query", [Field("rgb", Enum)])), indent="    "
    ) == dedent(
        """
        type Query {
            rgb: RGB
        }

        enum RGB {
            RED
            GREEN
            BLUE
        }
        """
    )


def test_custom_directive():
    directive = Directive(
        "customDirective",
        locations=["FIELD"],
        args=[Argument("argOne", String)],
    )
    schema = Schema(
        ObjectType("Query", [Field("foo", String)]), directives=[directive]
    )
    assert print_schema(schema, indent="    ") == dedent(
        """
        directive @customDirective(argOne: String) on FIELD

        type Query {
            foo: String
        }
        """
    )


def test_description_fits_on_one_line():
    assert print_schema(
        _single_field_schema(String, description="This field is awesome"),
        indent="    ",
        include_descriptions=True,
    ) == dedent(
        '''
        type Query {
            """This field is awesome"""
            singleField: String
        }
        '''
    )


def test_description_ends_with_a_quote():
    assert print_schema(
        _single_field_schema(String, description='This field is "awesome"'),
        indent="    ",
        include_descriptions=True,
    ) == dedent(
        '''
        type Query {
            """
            This field is "awesome"
            """
            singleField: String
        }
        '''
    )


def test_description_has_leading_space():
    assert print_schema(
        _single_field_schema(String, description='    This field is "awesome"'),
        indent="    ",
        include_descriptions=True,
    ) == dedent(
        '''
        type Query {
            """    This field is "awesome"
            """
            singleField: String
        }
        '''
    )


def test_introspection_schema(fixture_file):
    assert print_schema(
        Schema(),
        indent=2,
        include_introspection=True,
        use_legacy_comment_descriptions=False,
    ) == fixture_file("introspection-schema.graphql")


def test_introspection_schema_comments(fixture_file):
    assert print_schema(
        Schema(),
        indent=2,
        include_introspection=True,
        use_legacy_comment_descriptions=True,
    ) == fixture_file("intropsection-schema-comments.graphql")
