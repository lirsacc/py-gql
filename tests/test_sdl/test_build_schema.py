# -*- coding: utf-8 -*-

import pytest

from py_gql import graphql_blocking
from py_gql._string_utils import dedent
from py_gql.exc import SDLError
from py_gql.lang import parse
from py_gql.schema import SPECIFIED_DIRECTIVES, UUID
from py_gql.sdl import build_schema


def _check(schema):
    s = build_schema(schema)
    assert s.to_string() == dedent(schema)
    return s


def test_built_schema_is_executable():
    schema = build_schema(
        parse(
            """
            type Query {
                str: String
            }
            """,
            allow_type_system=True,
        )
    )
    data, _ = graphql_blocking(schema, "{ str }", root={"str": 123})
    assert data == {"str": "123"}


def test_accepts_strings():
    schema = build_schema(
        """
        type Query {
            str: String
        }
        """
    )
    data, _ = graphql_blocking(schema, "{ str }", root={"str": 123})
    assert data == {"str": "123"}


def test_simple_type():
    schema = """
    type Query {
        str: String
        int: Int
        float: Float
        id: ID
        bool: Boolean
    }
    """
    _check(schema)


def test_with_directive():
    schema = """
    directive @foo(arg: Int) on FIELD

    type Query {
        str: String
    }
    """
    _check(schema)


def test_descriptions_supports():
    schema = '''
    """This is a directive"""
    directive @foo(
        """It has an argument"""
        arg: Int
    ) on FIELD

    """With an enum"""
    enum Color {
        RED

        """Not a creative color"""
        GREEN
        BLUE
    }

    """What a great type"""
    type Query {
        """And a field to boot"""
        str: String
    }
    '''
    _check(schema)


def test_specified_directives_are_enforced():
    schema = build_schema(
        """
        directive @foo(arg: Int) on FIELD

        type Query {
            str: String
        }
        """
    )
    for d in SPECIFIED_DIRECTIVES:
        assert d is schema.directives[d.name]


def test_type_modifiers():
    _check(
        """
        type Query {
            nonNullStr: String!
            listOfStrs: [String]
            listOfNonNullStrs: [String!]
            nonNullListOfStrs: [String]!
            nonNullListOfNonNullStrs: [String!]!
        }
        """
    )


def test_recursive_type():
    _check(
        """
        type Query {
            str: String
            recurse: Query
        }
        """
    )


def test_circular_types():
    _check(
        """
        schema {
            query: TypeOne
        }

        type TypeOne {
            str: String
            typeTwo: TypeTwo
        }

        type TypeTwo {
            str: String
            typeOne: TypeOne
        }
        """
    )


def test_single_argument_field():
    _check(
        """
        type Query {
            str(int: Int): String
            floatToStr(float: Float): String
            idToStr(id: ID): String
            booleanToStr(bool: Boolean): String
            strToStr(bool: String): String
        }
        """
    )


def test_multiple_arguments():
    _check(
        """
        type Query {
            str(int: Int, bool: Boolean): String
        }
        """
    )


def test_simple_interface():
    _check(
        """
        type Query implements WorldInterface {
            str: String
        }

        interface WorldInterface {
            str: String
        }
        """
    )


def test_simple_output_enum():
    _check(
        """
        enum Hello {
            WORLD
        }

        type Query {
            hello: Hello
        }
        """
    )


def test_simple_input_enum():
    _check(
        """
        enum Hello {
            WORLD
        }

        type Query {
            str(hello: Hello): String
        }
        """
    )


def test_multiple_values_enum():
    _check(
        """
        enum Hello {
            WO
            RLD
        }

        type Query {
            hello: Hello
        }
        """
    )


def test_union():
    _check(
        """
        union Hello = WorldOne | WorldTwo

        type Query {
            hello: Hello
        }

        type WorldOne {
            str: String
        }

        type WorldTwo {
            str: String
        }
        """
    )


def test_executing_union_default_resolve_type():
    schema = build_schema(
        """
        type Query {
            fruits: [Fruit]
        }

        union Fruit = Apple | Banana

        type Apple {
            color: String
        }

        type Banana {
            length: Int
        }
        """
    )

    data, _ = graphql_blocking(
        schema,
        """
        {
            fruits {
                ... on Apple {
                    color
                }
                ... on Banana {
                    length
                }
            }
        }
        """,
        root={
            "fruits": [
                {"color": "green", "__typename__": "Apple"},
                {"length": 5, "__typename__": "Banana"},
            ]
        },
    )

    assert data == {"fruits": [{"color": "green"}, {"length": 5}]}


def test_executing_interface_default_resolve_type():
    schema = build_schema(
        """
        type Query {
            characters: [Character]
        }

        interface Character {
            name: String!
        }

        type Human implements Character {
            name: String!
            totalCredits: Int
        }

        type Droid implements Character {
            name: String!
            primaryFunction: String
        }
        """
    )

    data, _ = graphql_blocking(
        schema,
        """
        {
            characters {
                name
                ... on Human {
                    totalCredits
                }
                ... on Droid {
                    primaryFunction
                }
            }
        }
        """,
        root={
            "characters": [
                {
                    "name": "Han Solo",
                    "totalCredits": 10,
                    "__typename__": "Human",
                },
                {
                    "name": "R2-D2",
                    "primaryFunction": "Astromech",
                    "__typename__": "Droid",
                },
            ]
        },
    )

    assert data == {
        "characters": [
            {"name": "Han Solo", "totalCredits": 10},
            {"name": "R2-D2", "primaryFunction": "Astromech"},
        ]
    }


def test_custom_scalar():
    schema = _check(
        """
        scalar CustomScalar

        type Query {
            customScalar: CustomScalar
        }
        """
    )
    scalar = schema.types["CustomScalar"]
    assert scalar.parse("foo") == "foo"
    assert scalar.serialize(123) == 123


def test_input_object():
    _check(
        """
        input Input {
            int: Int
        }

        type Query {
            field(in: Input): String
        }
        """
    )


def test_input_object_with_default_value():
    _check(
        """
        input Input {
            int: Int = 42
        }

        type Query {
            field(in: Input): String
        }
        """
    )


def test_simple_argument_field_with_default():
    _check(
        """
        type Query {
            str(int: Int = 2): String
        }
        """
    )


def test_custom_scalar_argument_field_with_default():
    _check(
        """
        scalar CustomScalar

        type Query {
            str(int: CustomScalar = 2): String
        }
        """
    )


def test_simple_type_with_mutation():
    _check(
        """
        schema {
            query: HelloScalars
            mutation: Mutation
        }

        type HelloScalars {
            str: String
            int: Int
            bool: Boolean
        }

        type Mutation {
            addHelloScalars(str: String, int: Int, bool: Boolean): HelloScalars
        }
        """
    )


def test_simple_type_with_subscription():
    _check(
        """
        schema {
            query: HelloScalars
            subscription: Subscription
        }

        type HelloScalars {
            str: String
            int: Int
            bool: Boolean
        }

        type Subscription {
            sbscribeHelloScalars(str: String, int: Int, bool: Boolean): HelloScalars
        }
        """
    )


def test_unreferenced_type_implementing_referenced_interface():
    _check(
        """
        type Concrete implements Iface {
            key: String
        }

        interface Iface {
            key: String
        }

        type Query {
            iface: Iface
        }
        """
    )


def test_unreferenced_type_implementing_referenced_union():
    _check(
        """
        type Concrete {
            key: String
        }

        type Query {
            union: Union
        }

        union Union = Concrete
        """
    )


def test_supports_deprecated():
    _check(
        """
        enum MyEnum {
            VALUE
            OLD_VALUE @deprecated
            OTHER_VALUE @deprecated(reason: "Terrible reasons")
        }

        type Query {
            field1: String @deprecated
            field2: Int @deprecated(reason: "Because I said so")
            enum: MyEnum
        }
        """
    )


def test_root_operation_types_with_custom_names():
    schema = build_schema(
        """
        schema {
            query: SomeQuery
            mutation: SomeMutation
            subscription: SomeSubscription
        }
        type SomeQuery { str: String }
        type SomeMutation { str: String }
        type SomeSubscription { str: String }
        """
    )

    assert schema.query_type.name == "SomeQuery"  # type: ignore
    assert schema.mutation_type.name == "SomeMutation"  # type: ignore
    assert schema.subscription_type.name == "SomeSubscription"  # type: ignore


def test_default_root_operation_type_names():
    schema = build_schema(
        """
        type Query { str: String }
        type Mutation { str: String }
        type Subscription { str: String }
        """
    )

    assert schema.query_type.name == "Query"  # type: ignore
    assert schema.mutation_type.name == "Mutation"  # type: ignore
    assert schema.subscription_type.name == "Subscription"  # type: ignore


def test_allows_only_a_single_schema_definition():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
            }

            schema {
                query: Hello
            }

            type Hello {
                bar: Bar
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 6}],
        "message": "More than one schema definition in document",
    }


def test_allows_only_a_single_query_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
                query: Yellow
            }

            type Hello {
                bar: String
            }

            type Yellow {
                isColor: Boolean
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 2}, {"column": 17, "line": 4}],
        "message": "Schema must only define a single query operation",
    }


def test_allows_only_a_single_mutation_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
                mutation: Hello
                mutation: Yellow
            }

            type Hello {
                bar: String
            }

            type Yellow {
                isColor: Boolean
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 2}, {"column": 17, "line": 5}],
        "message": "Schema must only define a single mutation operation",
    }


def test_allows_only_a_single_subscription_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
                subscription: Hello
                subscription: Yellow
            }

            type Hello {
                bar: String
            }

            type Yellow {
                isColor: Boolean
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 2}, {"column": 17, "line": 5}],
        "message": "Schema must only define a single subscription operation",
    }


def test_unknown_type_referenced():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
            }

            type Hello {
                bar: Bar
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 22, "line": 7}],
        "message": "Type Bar not found in document",
    }


def test_unknown_type_in_interface_list():
    with pytest.raises(SDLError) as exc_info:
        build_schema("type Query implements Bar { field: String }")
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 23, "line": 1}],
        "message": "Type Bar not found in document",
    }


def test_unknown_type_in_union_list():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            union TestUnion = Bar
            type Query { testUnion: TestUnion }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 31, "line": 2}],
        "message": "Type Bar not found in document",
    }


def test_unknown_query_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Wat
            }

            type Hello {
                str: String
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 24, "line": 3}],
        "message": "Type Wat not found in document",
    }


def test_unknown_mutation_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
                mutation: Wat
            }

            type Hello {
                str: String
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 27, "line": 4}],
        "message": "Type Wat not found in document",
    }


def test_unknown_subscription_type():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Hello
                subscription: Wat
            }

            type Hello {
                str: String
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 31, "line": 4}],
        "message": "Type Wat not found in document",
    }


def test_does_not_consider_operation_names_or_fragment_name():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Foo
            }

            query Foo { field }

            fragment Foo on Type { field }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 24, "line": 3}],
        "message": "Type Foo not found in document",
    }


def test_forbids_duplicate_type_definitions():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            schema {
                query: Repeated
            }

            type Repeated {
                id: Int
            }

            type Repeated {
                id: String
            }
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 10}],
        "message": "Duplicate type Repeated",
    }


def test_forbids_duplicate_directive_definition():
    with pytest.raises(SDLError) as exc_info:
        build_schema(
            """
            type Query {
                foo: String
            }

            directive @foo on FIELD
            directive @foo on MUTATION
            """
        )
    assert exc_info.value.to_dict() == {
        "locations": [{"column": 13, "line": 7}],
        "message": "Duplicate directive @foo",
    }


def test_inject_custom_types():
    schema = build_schema(
        """
        type Query {
            foo: UUID
        }
        """,
        additional_types=[UUID],
    )
    assert schema.types["UUID"] is UUID


def test_build_schema_ignores_extensions_if_specified():
    assert (
        build_schema(
            """
            type Query {
                one: Int
            }

            extend type Object {
                one: Int
            }

            extend type Query {
                two: String
            }
            """,
            ignore_extensions=True,
        ).to_string()
        == dedent(
            """
            type Query {
                one: Int
            }
            """
        )
    )


def test_build_github_schema(fixture_file):
    build_schema(fixture_file("github-schema.graphql")).validate()
