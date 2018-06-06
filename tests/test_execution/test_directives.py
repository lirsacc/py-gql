# -*- coding: utf-8 -*-
""" execution tests related to directive handling """

import pytest

from py_gql.execution import execute
from py_gql.lang import parse
from py_gql.schema import (
    Schema, String, ObjectType, Field, Int, Arg, Directive)


test_type = ObjectType('TestType', [Field('a', String), Field('b', String)])
schema = Schema(test_type)
root = {'a': lambda *_: 'a', 'b': lambda *_: 'b'}


def test_without_directives():
    data, errors = execute(schema, parse('{ a, b }'), initial_value=root)
    assert data == {'a': 'a', 'b': 'b'}
    assert errors == []


@pytest.mark.parametrize('directive,value,expected', [
    ('include', 'true', {'a': 'a', 'b': 'b'}),
    ('include', 'false', {'b': 'b'}),
    ('skip', 'true', {'b': 'b'}),
    ('skip', 'false', {'a': 'a', 'b': 'b'}),
])
def test_built_ins_on_scalars(directive, value, expected):
    query = '{ a @%s(if: %s), b }' % (directive, value)
    data, errors = execute(schema, parse(query), initial_value=root)
    assert data == expected
    assert errors == []


@pytest.mark.parametrize('directive,value,expected', [
    ('include', 'true', {'a': 'a', 'b': 'b'}),
    ('include', 'false', {}),
    ('skip', 'true', {}),
    ('skip', 'false', {'a': 'a', 'b': 'b'}),
])
def test_built_ins_on_fragment_spreads(directive, value, expected):
    query = '''
    { ...f @%s(if: %s) }
    fragment f on TestType { a, b }
    ''' % (directive, value)
    data, errors = execute(schema, parse(query), initial_value=root)
    assert data == expected
    assert errors == []


@pytest.mark.parametrize('directive,value,expected', [
    ('include', 'true', {'a': 'a', 'b': 'b'}),
    ('include', 'false', {'b': 'b'}),
    ('skip', 'true', {'b': 'b'}),
    ('skip', 'false', {'a': 'a', 'b': 'b'}),
])
def test_built_ins_on_inline_fragments(directive, value, expected):
    query = '''{
        b
        ... on TestType @%s(if: %s) { a }
    }''' % (directive, value)
    data, errors = execute(schema, parse(query), initial_value=root)
    assert data == expected
    assert errors == []


@pytest.mark.parametrize('directive,value,expected', [
    ('include', 'true', {'a': 'a', 'b': 'b'}),
    ('include', 'false', {'b': 'b'}),
    ('skip', 'true', {'b': 'b'}),
    ('skip', 'false', {'a': 'a', 'b': 'b'}),
])
def test_built_ins_on_anonymous_inline_fragments(directive, value, expected):
    query = '''{
        b
        ... @%s(if: %s) { a }
    }''' % (directive, value)
    data, errors = execute(schema, parse(query), initial_value=root)
    assert data == expected
    assert errors == []


@pytest.mark.parametrize('include,skip,expected', [
    ('true', 'false', {'a': 'a', 'b': 'b'}),
    ('true', 'true', {'b': 'b'}),
    ('false', 'true', {'b': 'b'}),
    ('false', 'false', {'b': 'b'}),
])
def test_include_and_skip(include, skip, expected):
    query = '{ a @include(if: %s) @skip(if: %s), b }' % (include, skip)
    data, errors = execute(schema, parse(query), initial_value=root)
    assert data == expected
    assert errors == []


def test_custom_directive_on_field(mocker):
    CustomDirective = Directive('custom', ['FIELD'], [
        Arg('a', String),
        Arg('b', Int),
    ])
    schema = Schema(test_type, directives=[CustomDirective])
    resolver = mocker.Mock()
    root = {'a': resolver}

    data, _ = execute(
        schema,
        parse('{ a @custom(a: "foo", b: 42) }'),
        initial_value=root
    )

    (_, _, _, info), _ = resolver.call_args

    assert info.directive_values('custom') == {'a': 'foo', 'b': 42}
