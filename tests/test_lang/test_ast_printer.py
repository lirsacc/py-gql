# -*- coding: utf-8 -*-

from py_gql._string_utils import dedent
from py_gql.lang import ast as _ast, parse, print_ast
from py_gql.lang.printer import ASTPrinter


def test_minimal_ast():
    assert print_ast(_ast.Field(name=_ast.Name(value="foo"))) == "foo"


def test_query_operation_without_name():
    assert print_ast(parse("query { id, name }")) == dedent(
        """
    {
      id
      name
    }
    """
    )


def test_query_operation_without_name_and_artifacts():
    assert (
        print_ast(
            parse(
                """
        query ($foo: TestType) @testDirective { id, name }
    """
            )
        )
        == dedent(
            """
    query ($foo: TestType) @testDirective {
      id
      name
    }
    """
        )
    )


def test_mutation_operation_without_name():
    assert print_ast(parse("mutation { id, name }")) == dedent(
        """
    mutation {
      id
      name
    }
    """
    )


def test_mutation_operation_without_name_and_artifacts():
    assert (
        print_ast(
            parse(
                """
        mutation ($foo: TestType) @testDirective { id, name }
    """
            )
        )
        == dedent(
            """
    mutation ($foo: TestType) @testDirective {
      id
      name
    }
    """
        )
    )


def test_block_string_single_line_with_leading_space():
    assert (
        print_ast(
            parse(
                '''
        { field(arg: """    space-led value""") }
    '''
            )
        )
        == dedent(
            '''
    {
      field(arg: """    space-led value""")
    }
    '''
        )
    )


def test_block_string_string_with_a_first_line_indentation():
    ast = parse(
        '''
        {
          field(arg: """
                first
              line
            indentation
          """)
        }
    '''
    )
    assert print_ast(ast) == dedent(
        '''
    {
      field(arg: """
            first
          line
        indentation
      """)
    }
    '''
    )


def test_block_string_single_line_with_leading_space_and_quotation():
    ast = parse(
        '''
    {
      field(arg: """    space-led value "quoted string"
      """)
    }
    '''
    )
    assert print_ast(ast) == dedent(
        '''
    {
      field(arg: """    space-led value "quoted string"
      """)
    }
    '''
    )


# NOTE: Experimental
def test_fragment_defined_variables():
    ast = parse(
        """
    fragment Foo($a: ComplexType, $b: Boolean = false) on TestType {
        id
    }
    """,
        experimental_fragment_variables=True,
    )
    assert print_ast(ast) == dedent(
        """
    fragment Foo($a: ComplexType, $b: Boolean = false) on TestType {
      id
    }
    """
    )


def test_kitchen_sink(fixture_file):
    ks = fixture_file("kitchen-sink.graphql")
    assert print_ast(parse(ks)) == dedent(
        '''
query queryName($foo: ComplexType, $site: Site = MOBILE) {
  whoever123is: node(id: [123, 456]) {
    id
    ... on User @defer {
      field2 {
        id
        alias: field1(first: 10, after: $foo) @include(if: $foo) {
          id
          ...frag
        }
      }
    }
    ... @skip(unless: $foo) {
      id
    }
    ... {
      id
    }
  }
}

mutation likeStory {
  like(story: 123) @defer {
    story {
      id
    }
  }
}

subscription StoryLikeSubscription($input: StoryLikeSubscribeInput) {
  storyLikeSubscribe(input: $input) {
    story {
      likers {
        count
      }
      likeSentence {
        text
      }
    }
  }
}

fragment frag on Friend {
  foo(size: $size, bar: $b, obj: {key: "value", block: """
    block string uses \\"""
  """})
}

{
  unnamed(truthy: true, falsey: false, nullish: null)
  query
}
'''
    )


def test_schema_kitchen_sink(fixture_file):
    ks = fixture_file("schema-kitchen-sink.graphql")
    assert print_ast(parse(ks, allow_type_system=True)) == dedent(
        '''
schema {
  query: QueryType
  mutation: MutationType
}

"""
This is a description
of the `Foo` type.
"""
type Foo implements Bar & Baz {
  one: Type
  two(argument: InputType!): Type
  three(argument: InputType, other: String): Int
  four(argument: String = "string"): String
  five(argument: [String] = ["string", "string"]): String
  six(argument: InputType = {key: "value"}): Type
  seven(argument: Int = null): Type
}

type AnnotatedObject @onObject(arg: "value") {
  annotatedField(arg: Type = "default" @onArg): Type @onField
}

type UndefinedType

extend type Foo {
  seven(argument: [String]): Type
}

extend type Foo @onType

interface Bar {
  one: Type
  four(argument: String = "string"): String
}

interface AnnotatedInterface @onInterface {
  annotatedField(arg: Type @onArg): Type @onField
}

interface UndefinedInterface

extend interface Bar {
  two(argument: InputType!): Type
}

extend interface Bar @onInterface

union Feed = Story | Article | Advert

union AnnotatedUnion @onUnion = A | B

union AnnotatedUnionTwo @onUnion = A | B

union UndefinedUnion

extend union Feed = Photo | Video

extend union Feed @onUnion

scalar CustomScalar

scalar AnnotatedScalar @onScalar

extend scalar CustomScalar @onScalar

enum Site {
  DESKTOP
  MOBILE
}

enum AnnotatedEnum @onEnum {
  ANNOTATED_VALUE @onEnumValue
  OTHER_VALUE
}

enum UndefinedEnum

extend enum Site {
  VR
}

extend enum Site @onEnum

input InputType {
  key: String!
  answer: Int = 42
}

input AnnotatedInput @onInputObject {
  annotatedField: Type @onField
}

input UndefinedInput

extend input InputType {
  other: Float = 1.23e4
}

extend input InputType @onInputObject

directive @skip(if: Boolean!) on FIELD | FRAGMENT_SPREAD | INLINE_FRAGMENT

directive @include(if: Boolean!) on FIELD | FRAGMENT_SPREAD | INLINE_FRAGMENT

directive @include2(if: Boolean!) on FIELD | FRAGMENT_SPREAD | INLINE_FRAGMENT

extend schema @onSchema

extend schema @onSchema {
  subscription: SubscriptionType
}
'''
    )


def test_comment_descriptions():
    node = _ast.ObjectTypeDefinition(
        name=_ast.Name(value="Foo"),
        description=_ast.StringValue(
            value="This is a description\nof the `Foo` type.", block=True
        ),
        fields=[
            _ast.FieldDefinition(
                name=_ast.Name(value="bar"),
                type=_ast.NamedType(name=_ast.Name(value="Bar")),
            )
        ],
    )

    assert ASTPrinter(indent=4, use_legacy_comment_descriptions=True)(
        node
    ) == dedent(
        """
        # This is a description
        # of the `Foo` type.
        type Foo {
            bar: Bar
        }"""
    )


# From a broken case
def test_custom_indentation_object():
    assert (
        ASTPrinter(indent=4)(
            parse(
                """
            {
                bar {
                    one
                        two
                    ... on Object {
                        three
                    }
                    ...A
                }
            }

            fragment A on Object {
                four
            five
            }
            """
            )
        )
        == dedent(
            """
            {
                bar {
                    one
                    two
                    ... on Object {
                        three
                    }
                    ...A
                }
            }

            fragment A on Object {
                four
                five
            }
            """
        )
    )


def test_variable_definitions():
    assert (
        print_ast(
            parse(
                """
                query Query(
                    $a: ComplexType,
                    $b: Boolean = false,
                    $c: String @foo,
                    $d: Int! = 42 @bar(value: 42)
                ) {
                    id
                }
                """,
            )
        )
        == dedent(
            """
        query Query($a: ComplexType, $b: Boolean = false, $c: String @foo, \
$d: Int! = 42 @bar(value: 42)) {
          id
        }
        """
        )
    )
