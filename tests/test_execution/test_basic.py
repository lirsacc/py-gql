# -*- coding: utf-8 -*-

from inspect import isawaitable

import pytest

from py_gql.exc import ExecutionError, ResolverError
from py_gql.execution import execute
from py_gql.lang import parse
from py_gql.schema import (
    ID,
    UUID,
    Argument,
    Boolean,
    Field,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    RegexType,
    Schema,
    String,
)

from ._test_utils import assert_execution, create_test_schema

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_raises_on_missing_operation(starwars_schema, executor_cls):
    with pytest.raises(ExecutionError) as exc_info:
        await assert_execution(
            starwars_schema,
            """
            fragment a on Character {
                ...b
            }
            fragment b on Character {
                ...a
            }
            """,
            executor_cls=executor_cls,
        )

    assert "Expected at least one operation" in str(exc_info.value)


async def test_uses_inline_operation_if_no_name_is_provided(executor_cls):
    await assert_execution(
        create_test_schema(String),
        "{ test }",
        initial_value={"test": "foo"},
        expected_data={"test": "foo"},
        executor_cls=executor_cls,
    )


async def test_uses_only_operation_if_no_name_is_provided(executor_cls):
    schema = create_test_schema(String)
    await assert_execution(
        schema,
        "query Example { test }",
        initial_value={"test": "foo"},
        expected_data={"test": "foo"},
        executor_cls=executor_cls,
    )


async def test_uses_named_operation_if_name_is_provided(executor_cls):
    schema = create_test_schema(String)
    await assert_execution(
        schema,
        "query Example1 { test } query Example2 { test }",
        initial_value={"test": "foo"},
        operation_name="Example1",
        expected_data={"test": "foo"},
        executor_cls=executor_cls,
    )


async def test_raises_if_no_operation_is_provided(executor_cls):
    schema = create_test_schema(String)
    with pytest.raises(ExecutionError) as exc_info:
        # This is an *invalid* query, but it should be an *executable* query.
        await assert_execution(
            schema,
            "fragment Example on Query { test }",
            executor_cls=executor_cls,
        )
    assert str(exc_info.value) == "Expected at least one operation definition"


async def test_raises_if_no_operation_name_is_provided_along_multiple_operations(
    executor_cls
):
    schema = create_test_schema(String)
    with pytest.raises(ExecutionError) as exc_info:
        # This is an *invalid* query, but it should be an *executable* query.
        await assert_execution(
            schema,
            "query Example { test } query OtherExample { test }",
            executor_cls=executor_cls,
        )
    assert str(exc_info.value) == (
        "Operation name is required when document contains multiple "
        "operation definitions"
    )


async def test_raises_if_unknown_operation_name_is_provided(executor_cls):
    schema = create_test_schema(String)
    with pytest.raises(ExecutionError) as exc_info:
        await assert_execution(
            schema,
            "query Example { test } query OtherExample { test }",
            operation_name="Foo",
            executor_cls=executor_cls,
        )
    assert str(exc_info.value) == 'No operation "Foo" in document'


async def test_it_raises_if_operation_type_is_not_supported(executor_cls):
    with pytest.raises(ExecutionError) as exc_info:
        await assert_execution(
            Schema(
                mutation_type=ObjectType("Mutation", [Field("test", String)])
            ),
            "{ test }",
            initial_value={"test": "foo"},
            executor_cls=executor_cls,
        )
    assert str(exc_info.value) == "Schema doesn't support query operation"


async def test_uses_mutation_schema_for_mutation_operation(
    mocker, executor_cls
):
    query = mocker.Mock(return_value="foo")
    mutation = mocker.Mock(return_value="foo")
    subscription = mocker.Mock(return_value="foo")

    def _f(resolver):
        return Field("test", String, resolver=resolver)

    schema = Schema(
        query_type=ObjectType("Query", [_f(query)]),
        mutation_type=ObjectType("Mutation", [_f(mutation)]),
        subscription_type=ObjectType("Subscription", [_f(subscription)]),
    )

    await assert_execution(
        schema,
        parse("mutation M { test }"),
        executor_cls=executor_cls,
        expected_data={"test": "foo"},
    )
    assert not query.call_count
    assert mutation.call_count == 1


async def test_forwarded_resolver_arguments(mocker, executor_cls):

    resolver = mocker.Mock(return_value="foo")
    context = mocker.Mock()
    root = mocker.Mock()

    field = Field("test", String, [Argument("arg", String)], resolver=resolver)
    query_type = ObjectType("Test", [field])
    doc = parse("query ($var: String) { result: test(arg: $var) }")
    schema = Schema(query_type)

    result = assert_execution(
        schema,
        doc,
        context_value=context,
        initial_value=root,
        variables={"var": 123},
        executor_cls=executor_cls,
    )

    if isawaitable(result):
        await result

    (parent_value, ctx, info), args = resolver.call_args

    assert info.field_definition is field
    assert info.parent_type is query_type
    assert info.path == ["result"]
    assert info.variables == {"var": "123"}
    assert info.schema is schema

    assert ctx is context
    assert parent_value is root

    assert args == {"arg": "123"}


async def test_merge_of_parallel_fragments(executor_cls):
    T = ObjectType(
        "Type",
        [
            Field("a", String, resolver=lambda *_: "Apple"),
            Field("b", String, resolver=lambda *_: "Banana"),
            Field("c", String, resolver=lambda *_: "Cherry"),
            Field("deep", lambda: T, resolver=lambda *_: dict()),
        ],
    )  # type: ObjectType

    schema = Schema(T)

    await assert_execution(
        schema,
        parse(
            """
            { a, ...FragOne, ...FragTwo }

            fragment FragOne on Type {
                b
                deep { b, deeper: deep { b } }
            }

            fragment FragTwo on Type {
                c
                deep { c, deeper: deep { c } }
            }
            """
        ),
        executor_cls=executor_cls,
        expected_data={
            "a": "Apple",
            "b": "Banana",
            "c": "Cherry",
            "deep": {
                "b": "Banana",
                "c": "Cherry",
                "deeper": {"b": "Banana", "c": "Cherry"},
            },
        },
    )


async def test_full_response_path_is_included_on_error(raiser, executor_cls):
    A = ObjectType(
        "A",
        [
            Field("nullableA", lambda: A, resolver=lambda *_: {}),
            Field("nonNullA", lambda: NonNullType(A), resolver=lambda *_: {}),
            Field(
                "raises",
                lambda: NonNullType(String),
                resolver=raiser(ResolverError, "Catch me if you can"),
            ),
        ],
    )  # type: ObjectType

    await assert_execution(
        Schema(
            ObjectType(
                "query", [Field("nullableA", lambda: A, resolver=lambda *_: {})]
            )
        ),
        """
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
        """,
        executor_cls=executor_cls,
        expected_data={
            "nullableA": {
                "aliasedA": {"nonNullA": {"anotherA": {"raises": None}}}
            }
        },
        expected_errors=[
            (
                "Catch me if you can",
                (134, 140),
                "nullableA.aliasedA.nonNullA.anotherA.raises",
            )
        ],
    )


async def test_it_does_not_include_illegal_fields(mocker, executor_cls):
    """ ...even if you skip validation """

    root = {
        "test": mocker.Mock(return_value="foo"),
        "thisIsIllegalDontIncludeMe": mocker.Mock(return_value="foo"),
    }

    await assert_execution(
        Schema(mutation_type=ObjectType("mutation", [Field("test", String)])),
        # This is an *invalid* query, but it should be an *executable* query.
        """
        mutation M {
            thisIsIllegalDontIncludeMe
        }
        """,
        initial_value=root,
        expected_data={},
        executor_cls=executor_cls,
    )

    root["thisIsIllegalDontIncludeMe"].assert_not_called()
    root["test"].assert_not_called()


def _resolve_article(id_):
    return {
        "id": id_,
        "isPublished": True,
        "title": "My Article " + str(id_),
        "body": "This is a post",
        "hidden": "This data is not exposed in the schema",
        "keywords": ["foo", "bar", 1, True, None],
    }


_JOHN_SMITH = {
    "id": 123,
    "name": "John Smith",
    "recentArticle": _resolve_article(1),
}

BlogImage = ObjectType(
    "Image", [Field("url", String), Field("width", Int), Field("height", Int)]
)

BlogArticle = ObjectType(
    "Article",
    [
        Field("id", String),
        Field("isPublished", Boolean),
        Field("author", lambda: BlogAuthor, resolver=lambda *_: _JOHN_SMITH),
        Field("title", String),
        Field("body", String),
        Field("keywords", ListType(String)),
    ],
)  # type: ObjectType

BlogAuthor = ObjectType(
    "Author",
    [
        Field("id", String),
        Field("name", String),
        Field(
            "pic",
            BlogImage,
            [Argument("width", Int), Argument("height", Int)],
            resolver=lambda *_, **args: {
                "url": "cdn://123",
                "width": args["width"],
                "height": args["height"],
            },
        ),
        Field("recentArticle", lambda: BlogArticle),
    ],
)  # type: ObjectType

BlogQuery = ObjectType(
    "Query",
    [
        Field(
            "article",
            BlogArticle,
            [Argument("id", ID)],
            resolver=lambda *_, **args: _resolve_article(args["id"]),
        ),
        Field(
            "feed",
            ListType(BlogArticle),
            resolver=lambda *_: [_resolve_article(i) for i in range(1, 11)],
        ),
    ],
)

_LIBRARY_SCHEMA = Schema(BlogQuery)

_LIBRARY_QUERY = """
{
    feed {
        id,
        title
    },
    article(id: "1") {
        ...articleFields,a
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
"""


async def test_executes_library_query_correctly_without_validation(
    executor_cls
):
    await assert_execution(
        _LIBRARY_SCHEMA,
        # This is an *invalid* query, but it should be an *executable* query.
        _LIBRARY_QUERY,
        executor_cls=executor_cls,
        expected_data={
            "article": {
                "author": {
                    "id": "123",
                    "name": "John Smith",
                    "pic": {"url": "cdn://123", "width": 640, "height": 480},
                    "recentArticle": {
                        "id": "1",
                        "isPublished": True,
                        "title": "My Article 1",
                        "body": "This is a post",
                        "keywords": ["foo", "bar", "1", "true", None],
                    },
                },
                "body": "This is a post",
                "id": "1",
                "isPublished": True,
                "title": "My Article 1",
            },
            "feed": [
                {"id": "1", "title": "My Article 1"},
                {"id": "2", "title": "My Article 2"},
                {"id": "3", "title": "My Article 3"},
                {"id": "4", "title": "My Article 4"},
                {"id": "5", "title": "My Article 5"},
                {"id": "6", "title": "My Article 6"},
                {"id": "7", "title": "My Article 7"},
                {"id": "8", "title": "My Article 8"},
                {"id": "9", "title": "My Article 9"},
                {"id": "10", "title": "My Article 10"},
            ],
        },
    )


# REVIEW: Is that test necessary?
async def test_result_is_ordered_according_to_query():
    """ check that deep iteration order of keys in result corresponds to order
    of appearance in query accounting for fragment use """
    data, _ = execute(_LIBRARY_SCHEMA, parse(_LIBRARY_QUERY))

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
        (
            "feed",
            [
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
                [("id", None), ("title", None)],
            ],
        ),
        (
            "article",
            [
                ("id", None),
                ("isPublished", None),
                ("title", None),
                ("body", None),
                (
                    "author",
                    [
                        ("id", None),
                        ("name", None),
                        (
                            "pic",
                            [("url", None), ("width", None), ("height", None)],
                        ),
                        (
                            "recentArticle",
                            [
                                ("id", None),
                                ("isPublished", None),
                                ("title", None),
                                ("body", None),
                                ("keywords", [None, None, None, None, None]),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ]


async def test_custom_scalar(executor_cls):

    Email = RegexType(
        "Email", r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    )

    schema = Schema(
        ObjectType("Query", [Field("foo", UUID), Field("bar", Email)])
    )

    await assert_execution(
        schema,
        """
        {
            foo
            bar
        }
        """,
        executor_cls=executor_cls,
        initial_value={
            "foo": "aff929fe-25a1-5e3d-8634-4c122f38d596",
            "bar": "gujwar@gagiv.kg",
        },
        expected_data={
            "foo": "aff929fe-25a1-5e3d-8634-4c122f38d596",
            "bar": "gujwar@gagiv.kg",
        },
    )


async def test_invalid_scalar(executor_cls):
    schema = Schema(ObjectType("Query", [Field("field", Int)]))

    await assert_execution(
        schema,
        "{ field }",
        executor_cls=executor_cls,
        initial_value={"field": "aff929fe-25a1"},
        expected_exc=(
            RuntimeError,
            (
                'Field "field" cannot be serialized as "Int": '
                "Int cannot represent non integer value: aff929fe-25a1"
            ),
        ),
    )
