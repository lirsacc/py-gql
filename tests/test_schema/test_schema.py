from typing import cast

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
    "Object",
    [Field("fieldName", String)],
    interfaces=[Interface],
)

DirInput = InputObjectType("DirInput", [InputField("field", String)])

WrappedDirInput = InputObjectType(
    "WrappedDirInput",
    [InputField("field", String)],
)

Dir = Directive(
    "dir",
    ["OBJECT"],
    [Argument("arg", DirInput), Argument("argList", ListType(WrappedDirInput))],
)

BlogImage = ObjectType(
    "Image",
    [Field("url", String), Field("width", Int), Field("height", Int)],
)

BlogAuthor = ObjectType(
    "Author",
    [
        Field("id", String),
        Field("name", String),
        Field(
            "pic",
            BlogImage,
            [Argument("width", Int), Argument("height", Int)],
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
            "Query",
            [Field("getObject", Interface, resolver=_null_resolver)],
        ),
        directives=[Dir],
    )
    assert not schema.is_possible_type(Interface, Implementing)


def test_Schema_is_possible_handles_non_object_types():
    schema = Schema(
        ObjectType(
            "Query",
            [Field("getObject", Interface, resolver=_null_resolver)],
        ),
        directives=[Dir],
    )
    assert not schema.is_possible_type(Interface, Int)


def test_Schema_is_possible_rejects_non_abstract_types():
    schema = Schema(
        ObjectType(
            "Query",
            [Field("getObject", Interface, resolver=_null_resolver)],
        ),
        directives=[Dir],
    )

    with pytest.raises(TypeError):
        schema.is_possible_type(Int, Implementing)  # type: ignore


def test_Schema_includes_input_types_only_used_in_directives():
    schema = Schema(
        ObjectType(
            "Query",
            [Field("getObject", Interface, resolver=_null_resolver)],
        ),
        directives=[Dir],
    )
    assert schema.get_type("DirInput") is DirInput
    assert schema.get_type("WrappedDirInput") is WrappedDirInput


def test_Schema_get_type_raises_on_unknown_type():
    schema = Schema(
        ObjectType(
            "Query",
            [Field("getObject", Interface, resolver=_null_resolver)],
        ),
        directives=[Dir],
    )
    with pytest.raises(UnknownType):
        schema.get_type("UnknownType")


def test_Schema_includes_nested_input_objects_in_the_map():
    NestedInputObject = InputObjectType(
        "NestedInputObject",
        [InputField("value", String)],
    )
    SomeInputObject = InputObjectType(
        "SomeInputObject",
        [InputField("nested", NestedInputObject)],
    )
    SomeMutation = ObjectType(
        "SomeMutation",
        [
            Field(
                "mutateSomething",
                BlogArticle,
                [Argument("input", SomeInputObject)],
            ),
        ],
    )
    SomeSubscription = ObjectType(
        "SomeSubscription",
        [
            Field(
                "subscribeToSomething",
                BlogArticle,
                [Argument("input", SomeInputObject)],
            ),
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
        "SomeSubtype",
        [Field("f", Int)],
        lambda: [SomeInterface],
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


class TestResolvers:
    def test_register_resolver_on_root_type(self):
        schema = Schema(ObjectType("Query", [Field("author", BlogAuthor)]))
        resolver = lambda *_, **__: None

        schema.register_resolver("Query", "author", resolver)

        assert schema.query_type.fields[0].resolver is resolver  # type: ignore

    def test_register_resolver_on_child_type(self):
        Object = ObjectType("Object", [Field("id", String)])
        schema = Schema(ObjectType("Query", [Field("foo", Object)]))
        resolver = lambda *_, **__: None

        schema.register_resolver("Object", "id", resolver)

        assert (
            schema.get_type("Object").fields[0].resolver is resolver  # type: ignore
        )

    def test_register_resolver_raises_on_unknown_type(self):
        Object = ObjectType("Object", [Field("id", String)])
        schema = Schema(ObjectType("Query", [Field("foo", Object)]))
        resolver = lambda *_, **__: None

        with pytest.raises(UnknownType):
            schema.register_resolver("Foo", "id", resolver)

    def test_register_resolver_raises_on_unknown_field(self):
        Object = ObjectType("Object", [Field("id", String)])
        schema = Schema(ObjectType("Query", [Field("foo", Object)]))
        resolver = lambda *_, **__: None

        with pytest.raises(SchemaError):
            schema.register_resolver("Object", "foo", resolver)

    def test_register_resolver_raises_on_override_by_default(self):
        resolver = lambda *_, **__: None
        Object = ObjectType("Object", [Field("id", String, resolver=resolver)])
        schema = Schema(ObjectType("Query", [Field("foo", Object)]))

        new_resolver = lambda *_, **__: None

        with pytest.raises(ValueError):
            schema.register_resolver("Object", "id", new_resolver)

    def test_register_resolver_does_not_raise_on_same_resolver(self):
        resolver = lambda *_, **__: None
        Object = ObjectType("Object", [Field("id", String, resolver=resolver)])
        schema = Schema(ObjectType("Query", [Field("foo", Object)]))
        schema.register_resolver("Object", "id", resolver)

    def test_register_resolver_accepts_override_with_flag(self):
        old_resolver = lambda *_, **__: None
        Object = ObjectType(
            "Object",
            [Field("id", String, resolver=old_resolver)],
        )
        schema = Schema(ObjectType("Query", [Field("foo", Object)]))

        resolver = lambda *_, **__: None
        schema.register_resolver("Object", "id", resolver, allow_override=True)

        assert (
            schema.get_type("Object").fields[0].resolver is resolver  # type: ignore
        )

    def test_register_subscription_works(self):
        Query = ObjectType("Query", [Field("id", String)])
        Subscription = ObjectType("Subscription", [Field("values", Int)])
        schema = Schema(Query, subscription_type=Subscription)

        schema.register_subscription("Subscription", "values", lambda *_: 42)

        assert (
            schema.subscription_type.field_map[  # type: ignore
                "values"
            ].subscription_resolver()
            == 42
        )

    def test_register_subscription_raises_on_missing_subscription_type(self):
        Query = ObjectType("Query", [Field("id", String)])
        schema = Schema(Query)

        with pytest.raises(UnknownType):
            schema.register_subscription(
                "Subscription",
                "values",
                lambda *_: 42,
            )

    def test_register_subscription_raises_on_missing_field(self):
        Query = ObjectType("Query", [Field("id", String)])
        Subscription = ObjectType("Subscription", [Field("values", Int)])
        schema = Schema(Query, subscription_type=Subscription)

        with pytest.raises(SchemaError):
            schema.register_subscription("Subscription", "value", lambda *_: 42)

    def test_register_subscription_raises_on_existing_resolver(self):
        Query = ObjectType("Query", [Field("id", String)])
        Subscription = ObjectType("Subscription", [Field("values", Int)])
        schema = Schema(Query, subscription_type=Subscription)

        schema.register_subscription("Subscription", "values", lambda *_: 42)

        with pytest.raises(ValueError):
            schema.register_subscription(
                "Subscription",
                "values",
                lambda *_: 42,
            )

    def test_register_default_resolver(self):
        Query = ObjectType("Query", [Field("id", String)])
        schema = Schema(Query)

        def query_default(root, ctx, info):
            return 42

        schema.register_default_resolver("Query", query_default)

        assert (
            cast(ObjectType, schema.get_type("Query")).default_resolver
            is query_default
        )

    def test_register_default_resolver_already_set(self):
        Query = ObjectType("Query", [Field("id", String)])
        schema = Schema(Query)

        def query_default(root, ctx, info):
            return 42

        def query_default_2(root, ctx, info):
            return 84

        schema.register_default_resolver("Query", query_default)

        with pytest.raises(ValueError):
            schema.register_default_resolver("Query", query_default_2)

        assert (
            cast(ObjectType, schema.get_type("Query")).default_resolver
            is query_default
        )

    def test_register_default_resolver_allow_override(self):
        Query = ObjectType("Query", [Field("id", String)])
        schema = Schema(Query)

        def query_default(root, ctx, info):
            return 42

        def query_default_2(root, ctx, info):
            return 84

        schema.register_default_resolver("Query", query_default)
        schema.register_default_resolver(
            "Query",
            query_default_2,
            allow_override=True,
        )

        assert (
            cast(ObjectType, schema.get_type("Query")).default_resolver
            is query_default_2
        )

    def test_resolver_decorator_with_wildcard(self):
        Query = ObjectType("Query", [Field("id", String)])
        schema = Schema(Query)

        @schema.resolver("Query.*")
        def query_default(root, ctx, info):
            return 42

        assert (
            cast(ObjectType, schema.get_type("Query")).default_resolver
            is query_default
        )

    def test_register_type_resolver(self):
        schema = Schema(ObjectType("Query", [Field("id", Implementing)]))

        def type_resolver(root, ctx, info):
            return None

        schema.register_type_resolver("Interface", type_resolver)
        assert (
            cast(InterfaceType, schema.get_type("Interface")).resolve_type
            is type_resolver
        )

    def test_type_resolver_decorator(self):
        schema = Schema(ObjectType("Query", [Field("id", Implementing)]))

        @schema.type_resolver("Interface")
        def type_resolver(root, ctx, info):
            return None

        assert (
            cast(InterfaceType, schema.get_type("Interface")).resolve_type
            is type_resolver
        )

    def test_register_type_resolver_override(self):
        schema = Schema(ObjectType("Query", [Field("id", Implementing)]))

        def type_resolver(root, ctx, info):
            return None

        def type_resolver2(root, ctx, info):
            return None

        schema.register_type_resolver("Interface", type_resolver)

        with pytest.raises(ValueError):
            schema.register_type_resolver("Interface", type_resolver2)

        schema.register_type_resolver(
            "Interface",
            type_resolver2,
            allow_override=True,
        )
        assert (
            cast(InterfaceType, schema.get_type("Interface")).resolve_type
            is type_resolver2
        )

    def test_register_type_resolver_on_invalid_type(self):
        schema = Schema(ObjectType("Query", [Field("id", Implementing)]))

        def type_resolver(root, ctx, info):
            return None

        with pytest.raises(SchemaError):
            schema.register_type_resolver("Object", type_resolver)

    def test_register_type_resolver_on_unknown_type(self):
        schema = Schema(ObjectType("Query", [Field("id", Implementing)]))

        def type_resolver(root, ctx, info):
            return None

        with pytest.raises(UnknownType):
            schema.register_type_resolver("IFace", type_resolver)
