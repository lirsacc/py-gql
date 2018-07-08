# -*- coding: utf-8 -*-
""" generic execution tests """

import json

import pytest

from py_gql.exc import ExecutionError, ResolverError, VariablesCoercionError
from py_gql.execution import execute
from py_gql.lang import parse
from py_gql.schema import (
    ID,
    Argument,
    Boolean,
    Field,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
    Type,
)

from ._test_utils import TESTED_EXECUTORS, check_execution


def test_raises_if_no_schema_is_provided():
    with pytest.raises(AssertionError) as exc_info:
        execute(None, parse("{ field }"))
    assert str(exc_info.value) == "Expected Schema object"


def test_expects_document(starwars_schema):
    with pytest.raises(AssertionError) as exc_info:
        execute(starwars_schema, None)
    assert str(exc_info.value) == "Expected document"


def test_raises_on_missing_operation(starwars_schema):
    with pytest.raises(ExecutionError) as exc_info:
        check_execution(
            starwars_schema,
            """
            fragment a on Character {
                ...b
            }
            fragment b on Character {
                ...a
            }
            """,
        )

    assert "Expected at least one operation" in str(exc_info.value)


def _test_schema(field):
    if isinstance(field, Type):
        return Schema(ObjectType("Query", [Field("test", field)]))
    else:
        return Schema(ObjectType("Query", [field]))


def test_it_uses_inline_operation_if_no_name_is_provided():
    check_execution(
        _test_schema(String),
        "{ test }",
        initial_value={"test": "foo"},
        expected_data={"test": "foo"},
    )


def test_it_uses_only_operation_if_no_name_is_provided():
    check_execution(
        _test_schema(String),
        "query Example { test }",
        initial_value={"test": "foo"},
        expected_data={"test": "foo"},
    )


def test_it_uses_named_operation_if_name_is_provided():
    check_execution(
        _test_schema(String),
        "query Example1 { test } query Example2 { test }",
        initial_value={"test": "foo"},
        operation_name="Example1",
        expected_data={"test": "foo"},
    )


def test_raises_if_no_operation_is_provided():
    with pytest.raises(ExecutionError) as exc_info:
        # This is an *invalid* query, but it should be an *executable* query.
        execute(
            _test_schema(String), parse("fragment Example on Query { test }")
        )
    assert str(exc_info.value) == "Expected at least one operation"


def test_raises_if_no_operation_name_is_provided_along_multiple_operations():
    with pytest.raises(ExecutionError) as exc_info:
        execute(
            _test_schema(String),
            parse("query Example { test } query OtherExample { test }"),
        )
    assert str(exc_info.value) == (
        "Operation name is required when document contains multiple "
        "operation definitions"
    )


def test_raises_if_unknown_operation_name_is_provided():
    with pytest.raises(ExecutionError) as exc_info:
        execute(
            _test_schema(String),
            parse("query Example { test } query OtherExample { test }"),
            operation_name="Foo",
        )
    assert str(exc_info.value) == 'No operation "Foo" found in document'


def test_it_raises_if_operation_type_is_not_supported():
    with pytest.raises(ExecutionError) as exc_info:
        assert execute(
            Schema(
                mutation_type=ObjectType("Mutation", [Field("test", String)])
            ),
            parse("{ test }"),
            initial_value={"test": "foo"},
        )
    assert str(exc_info.value) == "Schema doesn't support query operation"


def test_uses_mutation_schema_for_mutation_operation(mocker):
    query = mocker.Mock(return_value="foo")
    mutation = mocker.Mock(return_value="foo")
    subscription = mocker.Mock(return_value="foo")

    def _f(resolver):
        return Field("test", String, resolve=resolver)

    schema = Schema(
        query_type=ObjectType("Query", [_f(query)]),
        mutation_type=ObjectType("Mutation", [_f(mutation)]),
        subscription_type=ObjectType("Subscription", [_f(subscription)]),
    )

    execute(schema, parse("mutation M { test }"))
    assert not query.call_count
    assert mutation.call_count == 1


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_default_resolution_looks_up_key(exe_cls, exe_kwargs):
    schema = _test_schema(String)
    root = {"test": "testValue"}

    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            schema,
            "{ test }",
            initial_value=root,
            executor=executor,
            expected_data={"test": "testValue"},
            expected_errors=[],
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_default_resolution_looks_up_attribute(exe_cls, exe_kwargs):
    class TestObject(object):
        def __init__(self, value):
            self.test = value

    schema = _test_schema(String)
    root = TestObject("testValue")
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            schema,
            "{ test }",
            initial_value=root,
            executor=executor,
            expected_data={"test": "testValue"},
            expected_errors=[],
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_default_resolution_evaluates_methods(exe_cls, exe_kwargs):
    class Adder(object):
        def __init__(self, value):
            self._num = value

        def test(self, args, ctx, info):
            return self._num + args["addend1"] + ctx["addend2"]

    schema = _test_schema(Field("test", Int, [Argument("addend1", Int)]))
    root = Adder(700)

    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            schema,
            "{ test(addend1: 80) }",
            initial_value=root,
            context_value={"addend2": 9},
            executor=executor,
            expected_data={"test": 789},
            expected_errors=[],
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_default_resolution_evaluates_callables(exe_cls, exe_kwargs):
    data = {
        "a": lambda *_: "Apple",
        "b": lambda *_: "Banana",
        "c": lambda *_: "Cookie",
        "d": lambda *_: "Donut",
        "e": lambda *_: "Egg",
        "deep": lambda *_: data,
    }

    Fruits = ObjectType(
        "Fruits",
        [
            Field("a", String),
            Field("b", String),
            Field("c", String),
            Field("d", String),
            Field("e", String),
            Field("deep", lambda: Fruits),
        ],
    )

    schema = Schema(Fruits)

    with exe_cls(**exe_kwargs) as executor:
        data, errors = execute(
            schema,
            parse(
                """{
                    a, b, c, d, e
                    deep {
                        a
                        deep {
                            a
                        }
                    }
                }"""
            ),
            initial_value=data,
            executor=executor,
        ).result()

    assert errors == []
    assert data == {
        "a": "Apple",
        "b": "Banana",
        "c": "Cookie",
        "d": "Donut",
        "e": "Egg",
        "deep": {"a": "Apple", "deep": {"a": "Apple"}},
    }


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_merge_of_parallel_fragments(exe_cls, exe_kwargs):
    T = ObjectType(
        "Type",
        [
            Field("a", String, resolve=lambda *_: "Apple"),
            Field("b", String, resolve=lambda *_: "Banana"),
            Field("c", String, resolve=lambda *_: "Cherry"),
            Field("deep", lambda: T, resolve=lambda *_: dict()),
        ],
    )
    schema = Schema(T)

    with exe_cls(**exe_kwargs) as executor:
        data, errors = execute(
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
            executor=executor,
        ).result()

    assert errors == []
    assert data == {
        "a": "Apple",
        "b": "Banana",
        "c": "Cherry",
        "deep": {
            "b": "Banana",
            "c": "Cherry",
            "deeper": {"b": "Banana", "c": "Cherry"},
        },
    }


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_forwarded_resolver_arguments(mocker, exe_cls, exe_kwargs):

    resolver, context, root = mocker.Mock(), {}, {}

    field = Field("test", String, [Argument("arg", String)], resolve=resolver)
    query_type = ObjectType("Test", [field])
    doc = parse("query ($var: String) { result: test(arg: $var) }")
    schema = Schema(query_type)

    with exe_cls(**exe_kwargs) as executor:
        data, errors = execute(
            schema,
            doc,
            context_value=context,
            initial_value=root,
            variables={"var": 123},
            executor=executor,
        ).result()

        assert errors == []

        parent_value, args, ctx, info = resolver.call_args[0]

        assert info.field_def is field
        assert info.parent_type is query_type
        assert info.path == ["result"]
        assert info.variables == {"var": "123"}
        assert info.schema is schema
        assert info.operation is doc.definitions[0]
        assert info.executor is executor

        assert ctx is context
        assert parent_value is root

        assert args == {"arg": "123"}


NullNonNullDataType = ObjectType(
    "DataType",
    [
        Field("scalar", String),
        Field("scalarNonNull", NonNullType(String)),
        Field("nested", lambda: NullNonNullDataType),
        Field("nestedNonNull", lambda: NonNullType(NullNonNullDataType)),
    ],
)

NullAndNonNullSchema = Schema(NullNonNullDataType)


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_nullable_field(exe_cls, exe_kwargs):
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            NullAndNonNullSchema,
            "query Q { scalar }",
            initial_value=dict(scalar=None),
            expected_data={"scalar": None},
            expected_errors=[],
            executor=executor,
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_lazy_nullable_field(exe_cls, exe_kwargs):
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            NullAndNonNullSchema,
            "query Q { scalar }",
            initial_value=dict(scalar=lambda *_: None),
            expected_data={"scalar": None},
            expected_errors=[],
            executor=executor,
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_and_report_error_on_non_nullable_field(exe_cls, exe_kwargs):
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            NullAndNonNullSchema,
            "query Q { scalarNonNull }",
            initial_value=dict(scalarNonNull=None),
            expected_data={"scalarNonNull": None},
            expected_errors=[
                (
                    'Field "scalarNonNull" is not nullable',
                    (10, 23),
                    "scalarNonNull",
                )
            ],
            executor=executor,
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_and_report_error_on_lazy_non_nullable_field(exe_cls, exe_kwargs):
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            NullAndNonNullSchema,
            "query Q { scalarNonNull }",
            initial_value=dict(scalarNonNull=lambda *_: None),
            expected_data={"scalarNonNull": None},
            expected_errors=[
                (
                    'Field "scalarNonNull" is not nullable',
                    (10, 23),
                    "scalarNonNull",
                )
            ],
            executor=executor,
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_tree_of_nullable_fields(exe_cls, exe_kwargs):
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            NullAndNonNullSchema,
            """
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
            """,
            initial_value={
                "nested": {
                    "scalar": None,
                    "nested": {"scalar": None, "nested": None},
                }
            },
            expected_data={
                "nested": {
                    "nested": {"nested": None, "scalar": None},
                    "scalar": None,
                }
            },
            expected_errors=[],
            executor=executor,
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_and_report_errors_on_tree_of_non_nullable_fields(
    exe_cls, exe_kwargs
):

    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            NullAndNonNullSchema,
            """
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
            """,
            executor=executor,
            initial_value={
                "nestedNonNull": None,
                "nested": {"scalarNonNull": None, "nestedNonNull": None},
            },
            expected_data={
                "nested": {"nestedNonNull": None, "scalarNonNull": None},
                "nestedNonNull": None,
            },
            expected_errors=[
                (
                    'Field "nested.scalarNonNull" is not nullable',
                    (68, 81),
                    "nested.scalarNonNull",
                ),
                (
                    'Field "nested.nestedNonNull" is not nullable',
                    (102, 278),
                    "nested.nestedNonNull",
                ),
                (
                    'Field "nestedNonNull" is not nullable',
                    (313, 380),
                    "nestedNonNull",
                ),
            ],
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_nulls_out_errored_subtrees(raiser, exe_cls, exe_kwargs):
    doc = parse(
        """{
        sync,
        callable_error,
        callable,
        resolver_error,
        resolver,
    }"""
    )

    root = dict(
        sync="sync",
        callable_error=raiser(ResolverError, "callable_error"),
        callable=lambda *_: "callable",
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field("sync", String),
                Field("callable_error", String),
                Field("callable", String),
                Field(
                    "resolver_error",
                    String,
                    resolve=raiser(ResolverError, "resolver_error"),
                ),
                Field("resolver", String, resolve=lambda *_: "resolver"),
            ],
        )
    )

    with exe_cls(**exe_kwargs) as executor:
        data, errors = execute(
            schema, doc, initial_value=root, executor=executor
        ).result()

    assert data == {
        "sync": "sync",
        "callable_error": None,
        "callable": "callable",
        "resolver_error": None,
        "resolver": "resolver",
    }

    assert [(str(err), err.nodes[0].loc, err.path) for err in errors] == [
        ("callable_error", (24, 38), ["callable_error"]),
        ("resolver_error", (66, 80), ["resolver_error"]),
    ]


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_full_response_path_is_included_on_error(raiser, exe_cls, exe_kwargs):
    A = ObjectType(
        "A",
        [
            Field("nullableA", lambda: A, resolve=lambda *_: {}),
            Field("nonNullA", lambda: NonNullType(A), resolve=lambda *_: {}),
            Field(
                "raises",
                lambda: NonNullType(String),
                resolve=raiser(ResolverError, "Catch me if you can"),
            ),
        ],
    )
    schema = Schema(
        ObjectType(
            "query", [Field("nullableA", lambda: A, resolve=lambda *_: {})]
        )
    )

    doc = parse(
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
    """
    )

    with exe_cls(**exe_kwargs) as executor:
        data, errors = execute(schema, doc, executor=executor).result()

    assert data == {
        "nullableA": {"aliasedA": {"nonNullA": {"anotherA": {"raises": None}}}}
    }

    assert [(str(err), err.nodes[0].loc, err.path) for err in errors] == [
        (
            "Catch me if you can",
            (159, 165),
            ["nullableA", "aliasedA", "nonNullA", "anotherA", "raises"],
        )
    ]


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_it_does_not_include_illegal_fields(mocker, exe_cls, exe_kwargs):
    """ ...even if you skip validation """
    # This is an *invalid* query, but it should be an *executable* query.
    doc = parse(
        """
    mutation M {
        thisIsIllegalDontIncludeMe
    }
    """
    )

    schema = Schema(
        mutation_type=ObjectType("mutation", [Field("test", String)])
    )

    root = {
        "test": mocker.Mock(return_value="foo"),
        "thisIsIllegalDontIncludeMe": mocker.Mock(return_value="foo"),
    }

    with exe_cls(**exe_kwargs) as executor:
        result, _ = execute(
            schema, doc, initial_value=root, executor=executor
        ).result()
    assert result == {}

    assert not root["thisIsIllegalDontIncludeMe"].call_count


@pytest.fixture
def _complex_schema():
    BlogImage = ObjectType(
        "Image",
        [Field("url", String), Field("width", Int), Field("height", Int)],
    )

    BlogAuthor = ObjectType(
        "Author",
        [
            Field("id", String),
            Field("name", String),
            Field("pic", BlogImage, [Argument("width", Int), Argument("height", Int)]),
            Field("recentArticle", lambda: BlogArticle),
        ],
    )

    BlogArticle = ObjectType(
        "Article",
        [
            Field("id", String),
            Field("isPublished", Boolean),
            Field("author", BlogAuthor),
            Field("title", String),
            Field("body", String),
            Field("keywords", ListType(String)),
        ],
    )

    BlogQuery = ObjectType(
        "Query",
        [
            Field(
                "article",
                BlogArticle,
                [Argument("id", ID)],
                resolve=lambda _, args, *r: article(args["id"]),
            ),
            Field(
                "feed",
                ListType(BlogArticle),
                resolve=lambda *_: [article(i) for i in range(1, 11)],
            ),
        ],
    )

    def article(id):
        return {
            "id": id,
            "isPublished": True,
            "author": lambda *r: john_smith,
            "title": "My Article " + str(id),
            "body": "This is a post",
            "hidden": "This data is not exposed in the schema",
            "keywords": ["foo", "bar", 1, True, None],
        }

    john_smith = {
        "id": 123,
        "name": "John Smith",
        "recentArticle": article(1),
        "pic": lambda _, args, *r: {
            "url": "cdn://123",
            "width": args["width"],
            "height": args["height"],
        },
    }

    schema = Schema(BlogQuery)

    query = """
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
    """

    return schema, parse(query)


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_executes_correctly_without_validation(
    _complex_schema, exe_cls, exe_kwargs
):
    # This is an *invalid* query, but it should be an *executable* query.
    schema, doc = _complex_schema

    with exe_cls(**exe_kwargs) as executor:
        data, errors = execute(schema, doc, executor=executor).result()

    assert data == {
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
    }

    assert errors == []


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_result_is_ordered_according_to_query(
    _complex_schema, exe_cls, exe_kwargs
):
    """ check that deep iteration order of keys in result corresponds to order
    of appearance in query accounting for fragment use """
    # This is an *invalid* query, but it should be an *executable* query.
    schema, doc = _complex_schema
    with exe_cls(**exe_kwargs) as executor:
        data, _ = execute(schema, doc, executor=executor).result()

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


class TestNonNullArguments(object):
    schema_with_null_args = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "withNonNullArg",
                    String,
                    args=[Argument("cannotBeNull", NonNullType(String))],
                    resolve=lambda _, a, *__: json.dumps(
                        a.get("cannotBeNull", "NOT PROVIDED")
                    ),
                )
            ],
        )
    )

    def test_non_null_literal(self):
        check_execution(
            self.schema_with_null_args,
            """
            query {
                withNonNullArg (cannotBeNull: "literal value")
            }
            """,
            expected_data={"withNonNullArg": '"literal value"'},
            expected_errors=[],
        )

    def test_non_null_variable(self):
        check_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String!) {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            variables={"testVar": "variable value"},
            expected_data={"withNonNullArg": '"variable value"'},
            expected_errors=[],
        )

    def test_missing_variable_with_default(self):
        check_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String = "default value") {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            expected_data={"withNonNullArg": '"default value"'},
            expected_errors=[],
        )

    def test_missing(self):
        check_execution(
            self.schema_with_null_args,
            """
            query {
                withNonNullArg
            }
            """,
            expected_data={"withNonNullArg": None},
            expected_errors=[
                (
                    'Argument "cannotBeNull" of required type "String!" was '
                    "not provided",
                    (37, 51),
                    "withNonNullArg",
                )
            ],
        )

    def test_null_literal(self):
        check_execution(
            self.schema_with_null_args,
            """
            query {
                withNonNullArg (cannotBeNull: null)
            }
            """,
            expected_data={"withNonNullArg": None},
            expected_errors=[
                (
                    'Argument "cannotBeNull" of type "String!" was provided '
                    "invalid value null (Expected non null value.)",
                    (37, 72),
                    "withNonNullArg",
                )
            ],
        )

    def test_missing_variable(self):
        # Differs from reference implementation as a missing variable will
        # abort the full execution. This is consistent as all variables defined
        # must be used in an operation and so a missing variables for a non null
        # type should break.
        check_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String!) {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            expected_exc=VariablesCoercionError,
            expected_msg=(
                'Variable "$testVar" of required type "String!" was not '
                "provided."
            ),
        )

    def test_null_variable(self):
        # Differs from reference implementation as a null variable provided for
        # a non null type will abort the full execution.
        check_execution(
            self.schema_with_null_args,
            """
            query ($testVar: String!) {
                withNonNullArg (cannotBeNull: $testVar)
            }
            """,
            variables={"testVar": None},
            expected_exc=VariablesCoercionError,
            expected_msg=(
                'Variable "$testVar" of required type "String!" '
                "must not be null."
            ),
        )
