# -*- coding: utf-8 -*-

from py_gql import build_schema
from py_gql.schema import Argument, Field, Int, ObjectType, Schema, String

from ._test_utils import assert_sync_execution, create_test_schema


class TestDefaultResolver:
    def test_looks_up_key(self):
        assert_sync_execution(
            create_test_schema(String),
            "{ test }",
            initial_value={"test": "testValue"},
            expected_data={"test": "testValue"},
        )

    def test_looks_up_attribute(self):
        class TestObject:
            def __init__(self, value):
                self.test = value

        assert_sync_execution(
            create_test_schema(String),
            "{ test }",
            initial_value=TestObject("testValue"),
            expected_data={"test": "testValue"},
        )

    def test_looks_up_key_with_custom_python_name(self):
        assert_sync_execution(
            create_test_schema(String, python_name="other_name"),
            "{ test }",
            initial_value={"other_name": "testValue"},
            expected_data={"test": "testValue"},
        )

    def test_looks_up_attribute_with_custom_python_name(self):
        class TestObject:
            def __init__(self, value):
                self.other_name = value

        assert_sync_execution(
            create_test_schema(String, python_name="other_name"),
            "{ test }",
            initial_value=TestObject("testValue"),
            expected_data={"test": "testValue"},
        )

    def test_evaluates_methods(self):
        class Adder:
            def __init__(self, value):
                self._num = value

            def test(self, ctx, *_, addend1):
                return self._num + addend1 + ctx["addend2"]

        schema = create_test_schema(
            Field("test", Int, [Argument("addend1", Int)])
        )
        root = Adder(700)

        assert_sync_execution(
            schema,
            "{ test(addend1: 80) }",
            initial_value=root,
            context_value={"addend2": 9},
            expected_data={"test": 789},
        )

    def test_evaluates_callables(self):
        data = {
            "a": lambda *_: "Apple",
            "b": lambda *_: "Banana",
            "c": lambda *_: "Cookie",
            "d": lambda *_: "Donut",
            "e": lambda *_: "Egg",
            "deep": lambda *_: data,  # type: ignore
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
        )  # type: ObjectType

        assert_sync_execution(
            Schema(Fruits),
            """{
                a, b, c, d, e
                deep {
                    a
                    deep {
                        a
                    }
                }
            }""",
            initial_value=data,
            expected_data={
                "a": "Apple",
                "b": "Banana",
                "c": "Cookie",
                "d": "Donut",
                "e": "Egg",
                "deep": {"a": "Apple", "deep": {"a": "Apple"}},
            },
        )


class TestOverrides:
    def _override_test_schema(self) -> Schema:
        return build_schema(
            """
            type Foo {
                a: Int
                b: Int!
            }

            type Query {
                foo: Foo!
            }
            """
        )

    def test_type_default_resolver_with_no_field_resolver(self):
        schema = self._override_test_schema()

        def default_foo(root, ctx, info, **kw):
            return 42

        schema.register_default_resolver("Foo", default_foo)

        assert_sync_execution(
            schema,
            "{ foo { b } }",
            {"foo": {"b": 42}},
            initial_value={"foo": {}},
        )

    def test_type_default_resolver_with_field_resolver(self):
        schema = self._override_test_schema()

        def default_foo(root, ctx, info, **args):
            return 42

        schema.register_default_resolver("Foo", default_foo)

        @schema.resolver("Foo.a")
        def resolve_foo_b(root, ctx, info, **kw):
            return 84

        assert_sync_execution(
            schema,
            "{ foo { a } }",
            {"foo": {"a": 84}},
            initial_value={"foo": {}},
        )

    def test_global_default_resolver_with_field_resolver(self):
        schema = self._override_test_schema()

        def default_foo(root, ctx, info, **kw):
            return 42

        schema.default_resolver = default_foo

        @schema.resolver("Foo.a")
        def resolve_foo_b(root, ctx, info, **kw):
            return 84

        assert_sync_execution(
            schema,
            "{ foo { a } }",
            {"foo": {"a": 84}},
            initial_value={"foo": {}},
        )

    def test_global_default_resolver_with_type_default_resolver(self):
        schema = self._override_test_schema()

        def default(root, ctx, info, **kw):
            return 42

        schema.default_resolver = default

        def default_foo(root, ctx, info, **kw):
            return 84

        schema.register_default_resolver("Foo", default_foo)

        assert_sync_execution(
            schema,
            "{ foo { a } }",
            {"foo": {"a": 84}},
            initial_value={"foo": {}},
        )

    def test_global_default_resolver(self):
        schema = self._override_test_schema()

        def default(root, ctx, info, **kw):
            return 42

        schema.default_resolver = default

        assert_sync_execution(
            schema,
            "{ foo { b } }",
            {"foo": {"b": 42}},
            initial_value={"foo": {}},
        )
