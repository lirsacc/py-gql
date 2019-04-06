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

DirInput = InputObjectType("DirInput", [InputField("field", String)])

WrappedDirInput = InputObjectType(
    "WrappedDirInput", [InputField("field", String)]
)

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
)  # type: ObjectType

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


def _null_resolver(*_a, **_kw):
    return {}


def test_Schema_is_possible_type_is_accurate():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolver=_null_resolver)]
        ),
        directives=[Dir],
    )
    assert not schema.is_possible_type(Interface, Implementing)


def test_Schema_is_possible_handles_non_object_types():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolver=_null_resolver)]
        ),
        directives=[Dir],
    )
    assert not schema.is_possible_type(Interface, Int)


def test_Schema_is_possible_rejects_non_abstract_types():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolver=_null_resolver)]
        ),
        directives=[Dir],
    )

    with pytest.raises(TypeError):
        schema.is_possible_type(Int, Implementing)  # type: ignore


def test_Schema_includes_input_types_only_used_in_directives():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolver=_null_resolver)]
        ),
        directives=[Dir],
    )
    assert schema.get_type("DirInput") is DirInput
    assert schema.get_type("WrappedDirInput") is WrappedDirInput


def test_Schema_get_type_raises_on_unknown_type():
    schema = Schema(
        ObjectType(
            "Query", [Field("getObject", Interface, resolver=_null_resolver)]
        ),
        directives=[Dir],
    )
    with pytest.raises(UnknownType):
        schema.get_type("UnknownType")


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


def test_assign_resolver_on_root_type():
    schema = Schema(ObjectType("Query", [Field("author", BlogAuthor)]))
    resolver = lambda *_, **__: None

    schema.assign_resolver("Query.author", resolver)

    assert schema.query_type.fields[0].resolver is resolver  # type: ignore


def test_assign_resolver_on_child_type():
    Object = ObjectType("Object", [Field("id", String)])
    schema = Schema(ObjectType("Query", [Field("foo", Object)]))
    resolver = lambda *_, **__: None

    schema.assign_resolver("Object.id", resolver)

    assert (
        schema.get_type("Object").fields[0].resolver is resolver  # type: ignore
    )


def test_assign_resolver_raises_on_unknown_type():
    Object = ObjectType("Object", [Field("id", String)])
    schema = Schema(ObjectType("Query", [Field("foo", Object)]))
    resolver = lambda *_, **__: None

    with pytest.raises(UnknownType):
        schema.assign_resolver("Foo.id", resolver)


def test_assign_resolver_raises_on_unknown_field():
    Object = ObjectType("Object", [Field("id", String)])
    schema = Schema(ObjectType("Query", [Field("foo", Object)]))
    resolver = lambda *_, **__: None

    with pytest.raises(ValueError):
        schema.assign_resolver("Object.foo", resolver)


def test_assign_resolver_raises_on_override_by_default():
    resolver = lambda *_, **__: None
    Object = ObjectType("Object", [Field("id", String, resolver=resolver)])
    schema = Schema(ObjectType("Query", [Field("foo", Object)]))

    with pytest.raises(ValueError):
        schema.assign_resolver("Object.id", resolver)


def test_assign_resolver_accepts_override_with_flag():
    old_resolver = lambda *_, **__: None
    Object = ObjectType("Object", [Field("id", String, resolver=old_resolver)])
    schema = Schema(ObjectType("Query", [Field("foo", Object)]))

    resolver = lambda *_, **__: None
    schema.assign_resolver("Object.id", resolver, allow_override=True)

    assert (
        schema.get_type("Object").fields[0].resolver is resolver  # type: ignore
    )
