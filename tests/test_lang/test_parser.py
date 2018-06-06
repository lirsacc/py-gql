# -*- coding: utf-8 -*-
""" Parser tests.
Ported from: https://github.com/graphql/graphql-js/blob/master/src/language/__tests__/parser-test.js  # noqa: E501
on revision 8d1ae25de444a9b544a1fdc98e138ae91b77057c.
"""
# Test naming is not very 'pythonic' as I tried to keep a close match with the
# original ones for easy reference. Others were kept while they were specific
# to the implementation and are kept as skipped.

import pytest

from py_gql.exc import UnexpectedToken, GraphQLSyntaxError
from py_gql.lang import ast as _ast
from py_gql.lang.parser import parse, parse_value, parse_type


# Comparing dicts will result in better assertion diffs from pytest.
def assert_node_equal(ref, expected):
    assert _ast.node_to_dict(ref) == _ast.node_to_dict(expected)


@pytest.mark.skip("Irrelevant")
def test_it_asserts_that_a_source_to_parse_was_provided():
    pass


@pytest.mark.parametrize("value, error_cls, position, message", [
    (u'{', UnexpectedToken, 1, 'Expected Name but found <EOF>'),
    (u'\n{ ...MissingOn }\nfragment MissingOn Type',
     UnexpectedToken, 37, 'Expected "on" but found Type'),
    (u'{ field: {} }', UnexpectedToken, 9, 'Expected Name but found {'),
    (u'notanoperation Foo { field }', UnexpectedToken, 0, 'notanoperation'),
    (u'...', UnexpectedToken, 0, '...'),
])
def test_it_provides_useful_errors(value, error_cls, position, message):
    with pytest.raises(error_cls) as exc_info:
        parse(value)

    if position is not None:
        assert exc_info.value.position == position
    if message is not None:
        assert exc_info.value.message == message


@pytest.mark.skip("Irrelevant")
def test_it_parse_provides_useful_error_when_using_source():
    pass


def test_it_parses_variable_inline_values():
    # assert doesn't raise
    parse(u'{ field(complex: { a: { b: [ $var ] } }) }')


# [WARN] naming ??
def test_it_parses_constant_default_values():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(u'query Foo($x: Complex = { a: { b: [ $var ] } }) { field }')
    assert exc_info.value.position == 36
    assert exc_info.value.message == '$'


def test_it_does_not_accept_fragments_named_on():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(u'fragment on on on { on }')
    assert exc_info.value.position == 9
    assert exc_info.value.message == 'on'


def test_it_does_not_accept_fragments_spread_of_on():
    with pytest.raises(UnexpectedToken) as exc_info:
        parse(u'{ ...on }')
    assert exc_info.value.position == 8
    assert exc_info.value.message == 'Expected Name but found }'


def test_it_parses_multi_bytes_characters():
    source = u'''
        # This comment has a \u0A0A multi-byte character.
        { field(arg: "Has a \u0A0A multi-byte character.") }
      '''
    tree = parse(source, no_location=True)
    assert_node_equal(tree.definitions[0].selection_set.selections, [
        _ast.Field(
            name=_ast.Name(value='field'),
            arguments=[
                _ast.Argument(
                    name=_ast.Name(value='arg'),
                    value=_ast.StringValue(
                        value=u'Has a \u0A0A multi-byte character.'
                    ),
                )
            ]
        )
    ])


def test_it_parses_kitchen_sink(fixture_file):
    # assert doesn't raise
    source = fixture_file('kitchen-sink.graphql')
    assert parse(source, no_location=True)
    assert parse(source, no_location=True, allow_type_system=False)


@pytest.mark.parametrize("keyword", [
    (u'on'),
    (u'fragment'),
    (u'query'),
    (u'mutation'),
    (u'subscription'),
    (u'true'),
    (u'false'),
])
def test_it_allows_non_keywords_anywhere_a_name_is_allowed(keyword):
    fragment_name = keyword if keyword != 'on' else 'a'
    assert parse(u'''
    query %(keyword)s {
        ... %(fragment_name)s
        ... on %(keyword)s { field }
    }
    fragment %(fragment_name)s on Type {
        %(keyword)s(%(keyword)s: $%(keyword)s)
            @%(keyword)s(%(keyword)s: %(keyword)s)
    }''' % dict(keyword=keyword, fragment_name=fragment_name))


def test_it_parses_anonymous_mutation_operations():
    # assert doesn't raise
    assert parse(u'''
    mutation {
        mutationField
    }
    ''', no_location=True)


def test_it_parses_anonymous_subscription_operations():
    # assert doesn't raise
    assert parse(u'''
    subscription {
        subscriptionField
    }
    ''', no_location=True)


def test_it_parses_named_mutation_operations():
    assert parse(u'''
    mutation Foo {
        mutationField
    }
    ''', no_location=True)


def test_it_parses_named_subscription_operations():
    assert parse(u'''
    subscription Foo {
        subscriptionField
    }''', no_location=True)


def test_it_creates_ast():
    assert_node_equal(
        parse(u'''{
  node(id: 4) {
    id,
    name
  }
}
'''),
        _ast.Document(loc=(0, 41), definitions=[
            _ast.OperationDefinition(
                loc=(0, 40),
                operation='query',
                name=None,
                variable_definitions=[],
                directives=[],
                selection_set=_ast.SelectionSet(
                    loc=(0, 40),
                    selections=[
                        _ast.Field(
                            loc=(4, 38),
                            alias=None,
                            name=_ast.Name(
                                loc=(4, 8),
                                value='node'
                            ),
                            arguments=[
                                _ast.Argument(
                                    loc=(9, 14),
                                    name=_ast.Name(
                                        loc=(9, 11),
                                        value='id'
                                    ),
                                    value=_ast.IntValue(
                                        loc=(13, 14),
                                        value='4'
                                    ),
                                ),
                            ],
                            directives=[],
                            selection_set=_ast.SelectionSet(
                                loc=(16, 38),
                                selections=[
                                    _ast.Field(
                                        loc=(22, 24),
                                        alias=None,
                                        name=_ast.Name(
                                            loc=(22, 24),
                                            value='id'
                                        ),
                                        directives=[],
                                        arguments=[],
                                        selection_set=None,
                                    ),
                                    _ast.Field(
                                        loc=(30, 34),
                                        alias=None,
                                        name=_ast.Name(
                                            loc=(30, 34),
                                            value='name'
                                        ),
                                        directives=[],
                                        arguments=[],
                                        selection_set=None,
                                    ),
                                ]
                            ),
                        )
                    ]
                )
            )
        ])
    )


def test_it_creates_ast_from_nameless_query_without_variables():
    body = u'''query {
  node {
    id
  }
}
'''
    assert_node_equal(parse(body), _ast.Document(
        loc=(0, 30),
        definitions=[
            _ast.OperationDefinition(
                loc=(0, 29),
                operation='query',
                name=None,
                variable_definitions=[],
                directives=[],
                selection_set=_ast.SelectionSet(
                    loc=(6, 29),
                    selections=[
                        _ast.Field(
                            loc=(10, 27),
                            alias=None,
                            name=_ast.Name(loc=(10, 14), value='node'),
                            arguments=[],
                            directives=[],
                            selection_set=_ast.SelectionSet(
                                loc=(15, 27),
                                selections=[
                                    _ast.Field(
                                        loc=(21, 23),
                                        alias=None,
                                        name=_ast.Name(
                                            loc=(21, 23),
                                            value='id'
                                        ),
                                        arguments=[],
                                        directives=[],
                                        selection_set=None,
                                    ),
                                ]
                            )
                        )
                    ]
                )
            )
        ]
    ))


def test_it_allows_parsing_without_source_location_information():
    assert parse(u'{ id }', no_location=True).loc is None


def test_it_experimental_allows_parsing_fragment_defined_variables():
    with pytest.raises(GraphQLSyntaxError):
        parse(u'fragment a($v: Boolean = false) on t { f(v: $v) }')

    assert parse(u'fragment a($v: Boolean = false) on t { f(v: $v) }',
                 experimental_fragment_variables=True)


@pytest.mark.skip("Irrelevant (loc/source access is different)")
def test_it_contains_location_information_that_only_stringifys_start_end():
    pass


@pytest.mark.skip("Irrelevant (loc/source access is different)")
def test_it_contains_references_to_source():
    pass


@pytest.mark.skip("Irrelevant (loc/source access is different)")
def test_it_contains_references_to_start_and_end_tokens():
    pass


def test_parse_value_it_parses_null_value():
    assert_node_equal(parse_value(u'null'), _ast.NullValue(loc=(0, 4)))


def test_parse_value_it_parses_list_values():
    assert_node_equal(parse_value(u'[123 "abc"]'), _ast.ListValue(
        loc=(0, 11),
        values=[
            _ast.IntValue(loc=(1, 4), value='123'),
            _ast.StringValue(loc=(5, 10), value='abc'),
        ]
    ))


def test_parse_value_it_parses_block_strings():
    assert_node_equal(parse_value(u'["""long""" "short"]'), _ast.ListValue(
        loc=(0, 20),
        values=[
            _ast.StringValue(loc=(1, 11), value='long', block=True),
            _ast.StringValue(loc=(12, 19), value='short'),
        ]
    ))


def test_parse_value_raises_if_block_strings_are_disabled():
    with pytest.raises(UnexpectedToken):
        parse_value(u'""" foo """', allow_block_strings=False)


def test_parse_type_it_parses_well_known_types():
    assert_node_equal(parse_type(u'String'), _ast.NamedType(
        loc=(0, 6),
        name=_ast.Name(loc=(0, 6), value='String')
    ))


def test_parse_type_it_parses_custom_types():
    assert_node_equal(parse_type(u'MyType'), _ast.NamedType(
        loc=(0, 6),
        name=_ast.Name(loc=(0, 6), value='MyType')
    ))


def test_parse_type_it_parses_list_types():
    assert_node_equal(parse_type(u'[MyType]'), _ast.ListType(
        loc=(0, 8),
        type=_ast.NamedType(
            loc=(1, 7),
            name=_ast.Name(loc=(1, 7), value='MyType')
        )
    ))


def test_parse_type_it_parses_non_null_types():
    assert_node_equal(parse_type(u'MyType!'), _ast.NonNullType(
        loc=(0, 7),
        type=_ast.NamedType(
            loc=(0, 6),
            name=_ast.Name(loc=(0, 6), value='MyType')
        )
    ))


def test_parse_type_it_parses_nested_types():
    assert_node_equal(parse_type(u'[MyType!]'), _ast.ListType(
        loc=(0, 9),
        type=_ast.NonNullType(
            loc=(1, 8),
            type=_ast.NamedType(
                loc=(1, 7),
                name=_ast.Name(loc=(1, 7), value='MyType')
            )
        )
    ))

# Extra tests not in the reference
# Mostly discovered during testing other parts of the library
# ------------------------------------------------------------------------------


def test_parse_type_it_parses_nested_types_2():
    assert_node_equal(parse_type(u'[MyType!]!'), _ast.NonNullType(
        loc=(0, 10),
        type=_ast.ListType(
            loc=(0, 9),
            type=_ast.NonNullType(
                loc=(1, 8),
                type=_ast.NamedType(
                    loc=(1, 7),
                    name=_ast.Name(loc=(1, 7), value='MyType')
                )
            )
        )
    ))


def test_it_parses_inline_fragment_without_type():
    assert_node_equal(parse('''
    fragment validFragment on Pet {
        ... {
            name
        }
    }
    '''), _ast.Document(
        loc=(0, 88),
        definitions=[
            _ast.FragmentDefinition(
                loc=(5, 83),
                name=_ast.Name(loc=(14, 27), value='validFragment'),
                type_condition=_ast.NamedType(
                    loc=(31, 34),
                    name=_ast.Name(loc=(31, 34), value='Pet')
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
                                            loc=(63, 67),
                                            value='name'
                                        )
                                    )
                                ]
                            )
                        )
                    ]
                )
            )
        ]
    ))