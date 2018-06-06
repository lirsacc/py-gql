# -*- coding: utf-8 -*-
""" generic execution tests """

import pytest

from py_gql.exc import (
    SchemaError, DocumentValidationError, ResolverError, ExecutionError)
from py_gql.execution import execute
from py_gql.lang import parse
from py_gql.schema import (
    Schema, String, ObjectType, Field, Int, Arg, Boolean, ListType, ID, Type,
    NonNullType)
from ._test_utils import check_execution


def test_raises_if_no_schema_is_provided():
    with pytest.raises(AssertionError) as exc_info:
        execute(None, parse('{ field }'))
    assert str(exc_info.value) == 'Invalid schema'


def test_raises_if_invalid_schema_is_provided():
    with pytest.raises(SchemaError) as exc_info:
        execute(Schema(String), parse('{ field }'))
    assert str(exc_info.value) == 'Query must be ObjectType but got "String"'


def test_expects_document(starwars_schema):
    with pytest.raises(AssertionError) as exc_info:
        execute(starwars_schema, None)
    assert str(exc_info.value) == 'Expected document'


def test_raises_on_validation_error(starwars_schema):
    with pytest.raises(DocumentValidationError):
        execute(starwars_schema, parse('''
        fragment a on Character {
            ...b
        }
        fragment b on Character {
            ...a
        }
        '''))


def _test_schema(field):
    if isinstance(field, Type):
        return Schema(ObjectType('Query', [Field('test', field)]))
    else:
        return Schema(ObjectType('Query', [field]))


def test_it_uses_inline_operation_if_no_name_is_provided():
    assert execute(
        _test_schema(String),
        parse('{ test }'),
        initial_value={'test': 'foo'}
    ) == ({'test': 'foo'}, [])


def test_it_uses_only_operation_if_no_name_is_provided():
    assert execute(
        _test_schema(String),
        parse('query Example { test }'),
        initial_value={'test': 'foo'}
    ) == ({'test': 'foo'}, [])


def test_it_uses_named_operation_if_name_is_provided():
    assert execute(
        _test_schema(String),
        parse('query Example1 { test } query Example2 { test }'),
        initial_value={'test': 'foo'},
        operation_name='Example1',
    ) == ({'test': 'foo'}, [])


def test_raises_if_no_operation_is_provided():
    with pytest.raises(ExecutionError) as exc_info:
        execute(
            _test_schema(String),
            parse('fragment Example on Query { test }'),
            _skip_validation=True,
        )
    assert str(exc_info.value) == 'Must provide an operation'


def test_raises_if_no_operation_name_is_provided_along_multiple_operations():
    with pytest.raises(ExecutionError) as exc_info:
        execute(
            _test_schema(String),
            parse('query Example { test } query OtherExample { test }'),
        )
    assert str(exc_info.value) == (
        'Operation name is required when document contains multiple '
        'operation definitions'
    )


def test_raises_if_unknown_operation_name_is_provided():
    with pytest.raises(ExecutionError) as exc_info:
        execute(
            _test_schema(String),
            parse('query Example { test } query OtherExample { test }'),
            operation_name='Foo'
        )
    assert str(exc_info.value) == 'No operation "Foo" found in document'


def test_it_raises_if_operation_type_is_not_supported():
    with pytest.raises(ExecutionError) as exc_info:
        assert execute(
            Schema(mutation_type=ObjectType('Mutation', [
                Field('test', String)
            ])),
            parse('{ test }'),
            initial_value={'test': 'foo'}
        )
    assert str(exc_info.value) == "Schema doesn't support query operation"


def test_uses_mutation_schema_for_mutation_operation(mocker):
    query = mocker.Mock(return_value='foo')
    mutation = mocker.Mock(return_value='foo')
    subscription = mocker.Mock(return_value='foo')

    def _f(resolver):
        return Field('test', String, resolve=resolver)

    schema = Schema(
        query_type=ObjectType('Query', [_f(query)]),
        mutation_type=ObjectType('Mutation', [_f(mutation)]),
        subscription_type=ObjectType('Subscription', [_f(subscription)]),
    )

    execute(schema, parse('mutation M { test }'))
    assert not query.call_count
    assert mutation.call_count == 1


# Currenty haven't found a solution for the subscriptions interface
@pytest.mark.xfail
def test_uses_subscription_schema_for_subscription_operation(mocker):
    query = mocker.Mock(return_value='foo')
    mutation = mocker.Mock(return_value='foo')
    subscription = mocker.Mock(return_value='foo')

    def _f(resolver):
        return Field('test', String, resolve=resolver)

    schema = Schema(
        query_type=ObjectType('Query', [_f(query)]),
        mutation_type=ObjectType('Mutation', [_f(mutation)]),
        subscription_type=ObjectType('Subscription', [_f(subscription)]),
    )

    execute(schema, parse('subscription M { test }'))
    assert not query.call_count
    assert subscription.call_count == 1


def test_default_resolution_looks_up_key():
    schema = _test_schema(String)
    root = {'test': 'testValue'}
    data, errors = execute(schema, parse('''{ test }'''), initial_value=root)
    assert data == {'test': 'testValue'}
    assert errors == []


def test_default_resolution_looks_up_attribute():
    class TestObject(object):
        def __init__(self, value):
            self.test = value

    schema = _test_schema(String)
    root = TestObject('testValue')
    data, errors = execute(schema, parse('''{ test }'''), initial_value=root)
    assert data == {'test': 'testValue'}
    assert errors == []


def test_default_resolution_evaluates_methods():
    class Adder(object):
        def __init__(self, value):
            self._num = value

        def test(self, args, ctx, info):
            return self._num + args['addend1'] + ctx['addend2']

    schema = _test_schema(Field('test', Int, [Arg('addend1', Int)]))
    root = Adder(700)
    data, errors = execute(schema, parse('''{
        test(addend1: 80)
    }'''), initial_value=root, context={'addend2': 9})
    assert data == {'test': 789}
    assert errors == []


def test_default_resolution_evaluates_callables():
    data = {
        'a': lambda *_: 'Apple',
        'b': lambda *_: 'Banana',
        'c': lambda *_: 'Cookie',
        'd': lambda *_: 'Donut',
        'e': lambda *_: 'Egg',
        'deep': lambda *_: data
    }

    Fruits = ObjectType('Fruits', [
        Field('a', String),
        Field('b', String),
        Field('c', String),
        Field('d', String),
        Field('e', String),
        Field('deep', lambda: Fruits),
    ])

    schema = Schema(Fruits)

    data, errors = execute(schema, parse('''{
        a, b, c, d, e
        deep {
            a
            deep {
                a
            }
        }
    }'''), initial_value=data)

    assert errors == []
    assert data == {
        'a': 'Apple',
        'b': 'Banana',
        'c': 'Cookie',
        'd': 'Donut',
        'e': 'Egg',
        'deep': {
            'a': 'Apple',
            'deep': {
                'a': 'Apple',
            }
        }
    }


def test_merge_of_parallel_fragments():
    T = ObjectType('Type', [
        Field('a', String, resolve=lambda *_: 'Apple'),
        Field('b', String, resolve=lambda *_: 'Banana'),
        Field('c', String, resolve=lambda *_: 'Cherry'),
        Field('deep', lambda: T, resolve=lambda *_: dict()),
    ])
    schema = Schema(T)

    data, errors = execute(schema, parse('''
        { a, ...FragOne, ...FragTwo }

        fragment FragOne on Type {
            b
            deep { b, deeper: deep { b } }
        }

        fragment FragTwo on Type {
            c
            deep { c, deeper: deep { c } }
        }
    '''))

    assert errors == []
    assert data == {
        'a': 'Apple',
        'b': 'Banana',
        'c': 'Cherry',
        'deep': {
            'b': 'Banana',
            'c': 'Cherry',
            'deeper': {
                'b': 'Banana',
                'c': 'Cherry',
            }
        }
    }


def test_forwarded_resolver_arguments(mocker):

    resolver, context, root = mocker.Mock(), {}, {}

    field = Field('test', String, [Arg('arg', String)], resolve=resolver)
    query_type = ObjectType('Test', [field])
    doc = parse('query ($var: String) { result: test(arg: $var) }')
    schema = Schema(query_type)

    data, errors = execute(
        schema,
        doc,
        context=context,
        initial_value=root,
        variables={'var': 123},
    )

    assert errors == []

    parent_value, args, ctx, info = resolver.call_args[0]

    assert info.field_def is field
    assert info.parent_type is query_type
    assert info.path == ['result']
    assert info.variables == {'var': '123'}
    assert info.schema is schema
    assert info.operation is doc.definitions[0]

    assert ctx is context
    assert parent_value is root

    assert args == {'arg': '123'}


NullNonNullDataType = ObjectType('DataType', [
    Field('scalar', String),
    Field('scalarNonNull', NonNullType(String)),
    Field('nested', lambda: NullNonNullDataType),
    Field('nestedNonNull', lambda: NonNullType(NullNonNullDataType)),
])

NullAndNonNullSchema = Schema(NullNonNullDataType)


def test_nulls_nullable_field():
    check_execution(
        NullAndNonNullSchema,
        'query Q { scalar }',
        initial_value=dict(scalar=None),
        expected_data={
            'scalar': None,
        },
        expected_errors=[]
    )


def test_nulls_lazy_nullable_field():
    check_execution(
        NullAndNonNullSchema,
        'query Q { scalar }',
        initial_value=dict(scalar=lambda *_: None),
        expected_data={
            'scalar': None,
        },
        expected_errors=[]
    )


def test_nulls_and_report_error_on_non_nullable_field():
    check_execution(
        NullAndNonNullSchema,
        'query Q { scalarNonNull }',
        initial_value=dict(scalarNonNull=None),
        expected_data={
            'scalarNonNull': None,
        },
        expected_errors=[
            ('Field "scalarNonNull" is not nullable', (10, 23), 'scalarNonNull')
        ]
    )


def test_nulls_and_report_error_on_lazy_non_nullable_field():
    check_execution(
        NullAndNonNullSchema,
        'query Q { scalarNonNull }',
        initial_value=dict(scalarNonNull=lambda *_: None),
        expected_data={
            'scalarNonNull': None,
        },
        expected_errors=[
            ('Field "scalarNonNull" is not nullable', (10, 23), 'scalarNonNull')
        ]
    )


def test_nulls_tree_of_nullable_fields():
    check_execution(
        NullAndNonNullSchema,
        '''
        query Q {
            nested {
                scalar
                nested {
                    scalar
                    nested {
                        scalar
                    }
                }
            }
        }
        ''',
        initial_value={
            'nested': {
                'scalar': None,
                'nested': {
                    'scalar': None,
                    'nested': None,
                }
            }
        },
        expected_data={
            'nested': {
                'nested': {
                    'nested': None,
                    'scalar': None
                },
                'scalar': None
            },
        },
        expected_errors=[]
    )


def test_nulls_and_report_errors_on_tree_of_non_nullable_fields():
    check_execution(
        NullAndNonNullSchema,
        '''
        query Q {
            nested {
                scalarNonNull
                nestedNonNull {
                    scalar
                    nestedNonNull {
                        scalarNonNull
                    }
                }
            }
            nestedNonNull {
                scalarNonNull
            }
        }
        ''',
        initial_value={
            'nestedNonNull': None,
            'nested': {
                'scalarNonNull': None,
                'nestedNonNull': None
            }
        },
        expected_data={
            'nested': {
                'nestedNonNull': None,
                'scalarNonNull': None
            },
            'nestedNonNull': None,
        },
        expected_errors=[
            ('Field "nested.scalarNonNull" is not nullable',
             (56, 69), 'nested.scalarNonNull'),
            ('Field "nested.nestedNonNull" is not nullable',
             (86, 242), 'nested.nestedNonNull'),
            ('Field "nestedNonNull" is not nullable',
             (269, 328), 'nestedNonNull')
        ]
    )


def test_nulls_out_errored_subtrees(raiser):
    doc = parse('''{
        sync,
        callable_error,
        callable,
        resolver_error,
        resolver,
    }''')

    root = dict(
        sync='sync',
        callable_error=raiser(ResolverError, 'callable_error'),
        callable=lambda *_: 'callable',
    )

    schema = Schema(ObjectType('Query', [
        Field('sync', String),
        Field('callable_error', String),
        Field('callable', String),
        Field('resolver_error', String,
              resolve=raiser(ResolverError, 'resolver_error')),
        Field('resolver', String, resolve=lambda *_: 'resolver'),
    ]))

    data, errors = execute(schema, doc, initial_value=root)

    assert data == {
        'sync': 'sync',
        'callable_error': None,
        'callable': 'callable',
        'resolver_error': None,
        'resolver': 'resolver',
    }

    assert [(str(err), node.loc, path) for err, node, path in errors] == [
        ('callable_error', (24, 38), ['callable_error']),
        ('resolver_error', (66, 80), ['resolver_error']),
    ]


def test_full_response_path_is_included_on_error(raiser):
    A = ObjectType('A', [
        Field('nullableA', lambda: A, resolve=lambda *_: {}),
        Field('nonNullA', lambda: NonNullType(A), resolve=lambda *_: {}),
        Field('raises', lambda: NonNullType(String),
              resolve=raiser(ResolverError, 'Catch me if you can')),
    ])
    schema = Schema(ObjectType('query', [
        Field('nullableA', lambda: A, resolve=lambda *_: {}),
    ]))

    data, errors = execute(schema, parse('''
    query {
        nullableA {
            aliasedA: nullableA {
                nonNullA {
                    anotherA: nonNullA {
                        raises
                    }
                }
            }
        }
    }
    '''))

    assert data == {
        'nullableA': {
            'aliasedA': {
                'nonNullA': {
                    'anotherA': {
                        'raises': None
                    }
                }
            }
        }
    }

    assert [(str(err), node.loc, path) for err, node, path in errors] == [
        ('Catch me if you can', (159, 165),
         ['nullableA', 'aliasedA', 'nonNullA', 'anotherA', 'raises']),
    ]


def test_it_does_not_include_illegal_fields(mocker):
    """ ...even if you skip validation """
    doc = parse('''
    mutation M {
        thisIsIllegalDontIncludeMe
    }
    ''')

    schema = Schema(mutation_type=ObjectType('mutation', [
        Field('test', String)
    ]))

    root = {
        'test': mocker.Mock(return_value='foo'),
        'thisIsIllegalDontIncludeMe': mocker.Mock(return_value='foo'),
    }

    result, _ = execute(schema, doc, initial_value=root, _skip_validation=True)
    assert result == {}

    assert not root['thisIsIllegalDontIncludeMe'].call_count


@pytest.fixture
def _complex_schema():
    BlogImage = ObjectType('Image', [
        Field('url', String),
        Field('width', Int),
        Field('height', Int),
    ])

    BlogAuthor = ObjectType('Author', [
        Field('id', String),
        Field('name', String),
        Field('pic', BlogImage, [
            Arg('width', Int),
            Arg('height', Int),
        ]),
        Field('recentArticle', lambda: BlogArticle),
    ])

    BlogArticle = ObjectType('Article', [
        Field('id', String),
        Field('isPublished', Boolean),
        Field('author', BlogAuthor),
        Field('title', String),
        Field('body', String),
        Field('keywords', ListType(String)),
    ])

    BlogQuery = ObjectType('Query', [
        Field('article', BlogArticle, [
            Arg('id', ID)
        ], resolve=lambda _, args, *r: article(args['id'])),
        Field('feed', ListType(BlogArticle), resolve=lambda *_: [
            article(i) for i in range(1, 11)
        ])
    ])

    def article(id):
        return {
            'id': id,
            'isPublished': True,
            'author': lambda *r: john_smith,
            'title': 'My Article ' + str(id),
            'body': 'This is a post',
            'hidden': 'This data is not exposed in the schema',
            'keywords': ['foo', 'bar', 1, True, None],
        }

    john_smith = {
        'id': 123,
        'name': 'John Smith',
        'recentArticle': article(1),
        'pic': lambda _, args, *r: {
            'url': 'cdn://123',
            'width': args['width'],
            'height': args['height'],
        }
    }

    schema = Schema(BlogQuery)

    query = '''
    {
        feed {
            id,
            title
        },
        article(id: "1") {
            ...articleFields,
            author {
                id,
                name,
                pic(width: 640, height: 480) {
                    url,
                    width,
                    height
                },
                recentArticle {
                    ...articleFields,
                    keywords
                }
            }
        }
    }

    fragment articleFields on Article {
        id,
        isPublished,
        title,
        body,
        hidden,
        notdefined
    }
    '''

    return schema, parse(query)


def test_execution_raises_on_validation_failure(_complex_schema):
    schema, doc = _complex_schema

    with pytest.raises(DocumentValidationError) as exc_info:
        execute(schema, doc)

    assert len(exc_info.value.errors) == 2
    assert [
        (msg, [n.loc for n in nodes])
        for msg, nodes in exc_info.value.errors
    ] == [
        ('Cannot query field "hidden" on type "Article"', [(590, 596)]),
        ('Cannot query field "notdefined" on type "Article"', [(606, 616)])
    ]


def test_executes_correctly_without_validation(_complex_schema):
    schema, doc = _complex_schema
    data, errors = execute(schema, doc, _skip_validation=True)

    assert data == {
        'article': {
            'author': {
                'id': '123',
                'name': 'John Smith',
                'pic': {
                    'url': 'cdn://123',
                    'width': 640,
                    'height': 480,
                },
                'recentArticle': {
                    'id': '1',
                    'isPublished': True,
                    'title': 'My Article 1',
                    'body': 'This is a post',
                    'keywords': ['foo', 'bar', '1', 'true', None],
                }
            },
            'body': 'This is a post',
            'id': '1',
            'isPublished': True,
            'title': 'My Article 1',
        },
        'feed': [
            {'id': '1', 'title': 'My Article 1'},
            {'id': '2', 'title': 'My Article 2'},
            {'id': '3', 'title': 'My Article 3'},
            {'id': '4', 'title': 'My Article 4'},
            {'id': '5', 'title': 'My Article 5'},
            {'id': '6', 'title': 'My Article 6'},
            {'id': '7', 'title': 'My Article 7'},
            {'id': '8', 'title': 'My Article 8'},
            {'id': '9', 'title': 'My Article 9'},
            {'id': '10', 'title': 'My Article 10'}
        ]
    }

    assert errors == []


def test_result_is_ordered_according_to_query(_complex_schema):
    """ check that deep iteration order of keys in result corresponds to order
    of appearance in query accounting for fragment use """
    schema, doc = _complex_schema
    data, _ = execute(schema, doc, _skip_validation=True)

    def _extract_keys_in_order(d):
        if not isinstance(d, dict):
            return None
        keys = []
        for key, value in d.items():
            if isinstance(value, dict):
                keys.append((key, _extract_keys_in_order(value)))
            elif isinstance(value, list):
                keys.append((key, [_extract_keys_in_order(i) for i in value]))
            else:
                keys.append((key, None))
        return keys

    assert _extract_keys_in_order(data) == [
        ('feed', [
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)],
            [('id', None), ('title', None)]]),
        ('article', [
            ('id', None),
            ('isPublished', None),
            ('title', None),
            ('body', None),
            ('author', [
                ('id', None),
                ('name', None),
                ('pic', [
                    ('url', None),
                    ('width', None),
                    ('height', None)]),
                ('recentArticle', [
                    ('id', None),
                    ('isPublished', None),
                    ('title', None),
                    ('body', None),
                    ('keywords', [None, None, None, None, None])])])])
    ]