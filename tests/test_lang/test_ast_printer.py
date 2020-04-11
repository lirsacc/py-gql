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
    printed = fixture_file("schema-kitchen-sink.printed.graphql")
    assert printed == print_ast(parse(ks, allow_type_system=True))


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
