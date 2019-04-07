# -*- coding: utf-8 -*-

# Test naming is not very 'pythonic' as I tried to keep a close match with the
# original ones for easy reference. Others were kept while they were specific
# to the implementation and are kept as skipped.

import pytest

from py_gql.exc import GraphQLSyntaxError, UnexpectedToken
from py_gql.lang import ast as _ast
from py_gql.lang.parser import parse, parse_type, parse_value


# Comparing dicts will result in better assertion diffs from pytest.
def assert_node_equal(ref, expected):
    assert _ast._ast_to_json(ref) == _ast._ast_to_json(expected)


@pytest.mark.parametrize(
    "value, error_cls, position, message",
    [
        ("{", UnexpectedToken, 1, 'Expected Name but found "<EOF>"'),
        (
            "\n{ ...MissingOn }\nfragment MissingOn Type",
            UnexpectedToken,
            37,
            'Expected "on" but found "Type"',
        ),
        ("{ field: {} }", UnexpectedToken, 9, 'Expected Name but found "{"'),
        (
            "notanoperation Foo { field }",
            UnexpectedToken,
            0,
            'Unexpected "notanoperation"',
        ),
        ("...", UnexpectedToken, 0, 'Unexpected "..."'),
    ],
)
def test_it_provides_useful_errors(value, error_cls, position, message):
    with pytest.raises(error_cls) as exc_info:
        parse(value)

    if position is not None:
        assert exc_info.value.position == position
    if message is not None:
        assert exc_info.value.message == message


def test_it_parses_variable_inline_values():
    # assert doesn't raise
    parse("{ field(complex: { a: { b: [ $var ] } }) }")


def test_it_parses_constant_default_values():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("query Foo($x: Complex = { a: { b: [ $var ] } }) { field }")
    assert exc_info.value.position == 36
    assert exc_info.value.message == 'Unexpected "$"'


def test_it_does_not_accept_fragments_named_on():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("fragment on on on { on }")
    assert exc_info.value.position == 9
    assert exc_info.value.message == 'Unexpected "on"'


def test_it_does_not_accept_fragments_spread_of_on():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse("{ ...on }")
    assert exc_info.value.position == 8
    assert exc_info.value.message == 'Expected Name but found "}"'


def test_it_parses_multi_bytes_characters():
    source = """
        # This comment has a \u0A0A multi-byte character.
        { field(arg: "Has a \u0A0A multi-byte character.") }
      """
    tree = parse(source, no_location=True)
    assert_node_equal(
        tree.definitions[0].selection_set.selections,  # type: ignore
        [
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-byte character."
                        ),
                    )
                ],
            )
        ],
    )


def test_it_parses_kitchen_sink(fixture_file):
    # assert doesn't raise
    source = fixture_file("kitchen-sink.graphql")
    assert parse(source, no_location=True)
    assert parse(source, no_location=True, allow_type_system=False)


@pytest.mark.parametrize(
    "keyword",
    [
        ("on"),
        ("fragment"),
        ("query"),
        ("mutation"),
        ("subscription"),
        ("true"),
        ("false"),
    ],
)
def test_it_allows_non_keywords_anywhere_a_name_is_allowed(keyword):
    fragment_name = keyword if keyword != "on" else "a"
    assert parse(
        """
    query %(keyword)s {
        ... %(fragment_name)s
        ... on %(keyword)s { field }
    }
    fragment %(fragment_name)s on Type {
        %(keyword)s(%(keyword)s: $%(keyword)s)
            @%(keyword)s(%(keyword)s: %(keyword)s)
    }"""
        % dict(keyword=keyword, fragment_name=fragment_name)
    )


def test_it_parses_anonymous_mutation_operations():
    # assert doesn't raise
    assert parse(
        """
    mutation {
        mutationField
    }
    """,
        no_location=True,
    )


def test_it_parses_anonymous_subscription_operations():
    # assert doesn't raise
    assert parse(
        """
    subscription {
        subscriptionField
    }
    """,
        no_location=True,
    )


def test_it_parses_named_mutation_operations():
    assert parse(
        """
    mutation Foo {
        mutationField
    }
    """,
        no_location=True,
    )


def test_it_parses_named_subscription_operations():
    assert parse(
        """
    subscription Foo {
        subscriptionField
    }""",
        no_location=True,
    )


def test_it_creates_ast():
    assert_node_equal(
        parse(
            """{
  node(id: 4) {
    id,
    name
  }
}
"""
        ),
        _ast.Document(
            loc=(0, 41),
            definitions=[
                _ast.OperationDefinition(
                    loc=(0, 40),
                    operation="query",
                    name=None,
                    variable_definitions=[],
                    directives=[],
                    selection_set=_ast.SelectionSet(
                        loc=(0, 40),
                        selections=[
                            _ast.Field(
                                loc=(4, 38),
                                alias=None,
                                name=_ast.Name(loc=(4, 8), value="node"),
                                arguments=[
                                    _ast.Argument(
                                        loc=(9, 14),
                                        name=_ast.Name(loc=(9, 11), value="id"),
                                        value=_ast.IntValue(
                                            loc=(13, 14), value="4"
                                        ),
                                    )
                                ],
                                directives=[],
                                selection_set=_ast.SelectionSet(
                                    loc=(16, 38),
                                    selections=[
                                        _ast.Field(
                                            loc=(22, 24),
                                            alias=None,
                                            name=_ast.Name(
                                                loc=(22, 24), value="id"
                                            ),
                                            directives=[],
                                            arguments=[],
                                            selection_set=None,
                                        ),
                                        _ast.Field(
                                            loc=(30, 34),
                                            alias=None,
                                            name=_ast.Name(
                                                loc=(30, 34), value="name"
                                            ),
                                            directives=[],
                                            arguments=[],
                                            selection_set=None,
                                        ),
                                    ],
                                ),
                            )
                        ],
                    ),
                )
            ],
        ),
    )


def test_it_creates_ast_from_nameless_query_without_variables():
    body = """query {
  node {
    id
  }
}
"""
    assert_node_equal(
        parse(body),
        _ast.Document(
            loc=(0, 30),
            definitions=[
                _ast.OperationDefinition(
                    loc=(0, 29),
                    operation="query",
                    name=None,
                    variable_definitions=[],
                    directives=[],
                    selection_set=_ast.SelectionSet(
                        loc=(6, 29),
                        selections=[
                            _ast.Field(
                                loc=(10, 27),
                                alias=None,
                                name=_ast.Name(loc=(10, 14), value="node"),
                                arguments=[],
                                directives=[],
                                selection_set=_ast.SelectionSet(
                                    loc=(15, 27),
                                    selections=[
                                        _ast.Field(
                                            loc=(21, 23),
                                            alias=None,
                                            name=_ast.Name(
                                                loc=(21, 23), value="id"
                                            ),
                                            arguments=[],
                                            directives=[],
                                            selection_set=None,
                                        )
                                    ],
                                ),
                            )
                        ],
                    ),
                )
            ],
        ),
    )


def test_it_allows_parsing_without_source_location_information():
    assert parse("{ id }", no_location=True).loc is None


def test_it_experimental_allows_parsing_fragment_defined_variables():
    with pytest.raises(GraphQLSyntaxError):
        parse("fragment a($v: Boolean = false) on t { f(v: $v) }")

    assert parse(
        "fragment a($v: Boolean = false) on t { f(v: $v) }",
        experimental_fragment_variables=True,
    )


def test_it_contains_references_to_source():
    doc = parse("{ id }")
    assert doc.source == "{ id }"


def test_parse_value_it_parses_null_value():
    assert_node_equal(parse_value("null"), _ast.NullValue(loc=(0, 4)))


def test_parse_value_it_parses_list_values():
    assert_node_equal(
        parse_value('[123 "abc"]'),
        _ast.ListValue(
            loc=(0, 11),
            values=[
                _ast.IntValue(loc=(1, 4), value="123"),
                _ast.StringValue(loc=(5, 10), value="abc"),
            ],
        ),
    )


def test_parse_value_it_parses_block_strings():
    assert_node_equal(
        parse_value('["""long""" "short"]'),
        _ast.ListValue(
            loc=(0, 20),
            values=[
                _ast.StringValue(loc=(1, 11), value="long", block=True),
                _ast.StringValue(loc=(12, 19), value="short"),
            ],
        ),
    )


def test_parse_type_it_parses_well_known_types():
    assert_node_equal(
        parse_type("String"),
        _ast.NamedType(loc=(0, 6), name=_ast.Name(loc=(0, 6), value="String")),
    )


def test_parse_type_it_parses_custom_types():
    assert_node_equal(
        parse_type("MyType"),
        _ast.NamedType(loc=(0, 6), name=_ast.Name(loc=(0, 6), value="MyType")),
    )


def test_parse_type_it_parses_list_types():
    assert_node_equal(
        parse_type("[MyType]"),
        _ast.ListType(
            loc=(0, 8),
            type=_ast.NamedType(
                loc=(1, 7), name=_ast.Name(loc=(1, 7), value="MyType")
            ),
        ),
    )


def test_parse_type_it_parses_non_null_types():
    assert_node_equal(
        parse_type("MyType!"),
        _ast.NonNullType(
            loc=(0, 7),
            type=_ast.NamedType(
                loc=(0, 6), name=_ast.Name(loc=(0, 6), value="MyType")
            ),
        ),
    )


def test_parse_type_it_parses_nested_types():
    assert_node_equal(
        parse_type("[MyType!]"),
        _ast.ListType(
            loc=(0, 9),
            type=_ast.NonNullType(
                loc=(1, 8),
                type=_ast.NamedType(
                    loc=(1, 7), name=_ast.Name(loc=(1, 7), value="MyType")
                ),
            ),
        ),
    )


# Extra tests not in the reference
# Mostly discovered during testing other parts of the library
# ------------------------------------------------------------------------------


def test_parse_type_it_parses_nested_types_2():
    assert_node_equal(
        parse_type("[MyType!]!"),
        _ast.NonNullType(
            loc=(0, 10),
            type=_ast.ListType(
                loc=(0, 9),
                type=_ast.NonNullType(
                    loc=(1, 8),
                    type=_ast.NamedType(
                        loc=(1, 7), name=_ast.Name(loc=(1, 7), value="MyType")
                    ),
                ),
            ),
        ),
    )


def test_it_parses_inline_fragment_without_type():
    assert_node_equal(
        parse(
            """
    fragment validFragment on Pet {
        ... {
            name
        }
    }
    """
        ),
        _ast.Document(
            loc=(0, 88),
            definitions=[
                _ast.FragmentDefinition(
                    loc=(5, 83),
                    name=_ast.Name(loc=(14, 27), value="validFragment"),
                    type_condition=_ast.NamedType(
                        loc=(31, 34), name=_ast.Name(loc=(31, 34), value="Pet")
                    ),
                    variable_definitions=None,
                    selection_set=_ast.SelectionSet(
                        loc=(35, 83),
                        selections=[
                            _ast.InlineFragment(
                                loc=(45, 77),
                                selection_set=_ast.SelectionSet(
                                    loc=(49, 77),
                                    selections=[
                                        _ast.Field(
                                            loc=(63, 67),
                                            name=_ast.Name(
                                                loc=(63, 67), value="name"
                                            ),
                                        )
                                    ],
                                ),
                            )
                        ],
                    ),
                )
            ],
        ),
    )
