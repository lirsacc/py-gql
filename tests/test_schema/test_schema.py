# -*- coding: utf-8 -*-

import pytest

from py_gql.exc import SchemaError, UnknownType
from py_gql.schema import (
    Argument,
    Boolean,
    Directive,
    Field,
    InputField,
    InputObjectType,
    Int,
    InterfaceType,
    ListType,
    ObjectType,
    Schema,
    String,
)

Interface = InterfaceType("Interface", [Field("fieldName", String)])

Implementing = ObjectType(
    "Object", [Field("fieldName", String)], interfaces=[Interface]
)

DirInput = InputObjectType("DirInput", [Field("field", String)])

WrappedDirInput = InputObjectType("WrappedDirInput", [Field("field", String)])

Dir = Directive(
    "dir",
    ["OBJECT"],
    [Argument("arg", DirInput), Argument("argList", ListType(WrappedDirInput))],
)

BlogImage = ObjectType(
    "Image", [Field("url", String), Field("width", Int), Field("height", Int)]
)

BlogAuthor = ObjectType(
    "Author",
    [
        Field("id", String),
        Field("name", String),
        Field(
            "pic", BlogImage, [Argument("width", Int), Argument("height", Int)]
        ),
        Field("recentArticle", lambda: BlogArticle),
    ],
)

BlogArticle = ObjectType(
    "Article",
    [
        Field("id", String),
        Field("isPublished", Boolean),
        Field("author", lambda: BlogAuthor),
        Field("title", String),
        Field("body", String),
    ],
)

BlogQuery = ObjectType(
    "Query",
    [
        Field("article", BlogArticle, [Argument("id", String)]),
        Field("feed", ListType(BlogArticle)),
    ],
)

BlogMutation = ObjectType("Mutation", [Field("writeArticle", BlogArticle)])

BlogSubscription = ObjectType(
    "Subscription",
    [Field("articleSubscribe", BlogArticle, [Argument("id", String)])],
)


def _null_resolver(*a, **kw):
    return {}


def test_Schema_is_possible_type_is_accurate():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolve=_null_resolver)]
        ),
        directives=[Dir],
    )
    assert not schema.is_possible_type(Interface, Implementing)


def test_Schema_includes_input_types_only_used_in_directives():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolve=_null_resolver)]
        ),
        directives=[Dir],
    )
    assert schema.get_type("DirInput") is DirInput
    assert schema.get_type("WrappedDirInput") is WrappedDirInput


def test_Schema_get_type_raises_on_unknown_type():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolve=_null_resolver)]
        ),
        directives=[Dir],
    )
    with pytest.raises(UnknownType):
        schema.get_type("UnknownType")


def test_Schema_get_type_does_not_raise_on_unknown_type_with_default():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolve=_null_resolver)]
        ),
        directives=[Dir],
    )
    assert schema.get_type("UnknownType", None) is None


def test_Schema_includes_nested_input_objects_in_the_map():
    NestedInputObject = InputObjectType(
        "NestedInputObject", [InputField("value", String)]
    )
    SomeInputObject = InputObjectType(
        "SomeInputObject", [InputField("nested", NestedInputObject)]
    )
    SomeMutation = ObjectType(
        "SomeMutation",
        [
            Field(
                "mutateSomething",
                BlogArticle,
                [Argument("input", SomeInputObject)],
            )
        ],
    )
    SomeSubscription = ObjectType(
        "SomeSubscription",
        [
            Field(
                "subscribeToSomething",
                BlogArticle,
                [Argument("input", SomeInputObject)],
            )
        ],
    )

    schema = Schema(
        BlogQuery,
        mutation_type=SomeMutation,
        subscription_type=SomeSubscription,
    )

    assert schema.types.get("NestedInputObject") is NestedInputObject


def test_Schema_includes_interface_possible_types_in_the_type_map():
    SomeInterface = InterfaceType("SomeInterface", [Field("f", Int)])

    SomeSubtype = ObjectType(
        "SomeSubtype", [Field("f", Int)], lambda: [SomeInterface]
    )

    schema = Schema(
        ObjectType("Query", [Field("iface", SomeInterface)]),
        types=[SomeSubtype],
    )

    assert schema.types.get("SomeSubtype") is SomeSubtype


def test_Schema_refuses_duplicate_type_names():
    type_1 = ObjectType("Object", [Field("f", String)])
    type_2 = ObjectType("Object", [Field("f", String)])
    with pytest.raises(SchemaError) as exc_info:
        Schema(ObjectType("Query", [Field("f1", type_1), Field("f2", type_2)]))

    assert str(exc_info.value) == 'Duplicate type "Object"'


def test_Schema_includes_introspection_types():
    schema = Schema(ObjectType("Query", [Field("author", BlogAuthor)]))

    assert schema.get_type("__Schema") is not None
    assert schema.get_type("__Directive") is not None
    assert schema.get_type("__DirectiveLocation") is not None
    assert schema.get_type("__Type") is not None
    assert schema.get_type("__EnumValue") is not None
    assert schema.get_type("__InputValue") is not None
    assert schema.get_type("__Field") is not None
    assert schema.get_type("__TypeKind") is not None
