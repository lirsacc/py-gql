# -*- coding: utf-8 -*-

from py_gql.schema import Argument, Field, Int, ObjectType, Schema, String

from ._test_utils import assert_sync_execution, create_test_schema


def test_looks_up_key():
    assert_sync_execution(
        create_test_schema(String),
        "{ test }",
        initial_value={"test": "testValue"},
        expected_data={"test": "testValue"},
    )


def test_looks_up_attribute():
    class TestObject:
        def __init__(self, value):
            self.test = value

    assert_sync_execution(
        create_test_schema(String),
        "{ test }",
        initial_value=TestObject("testValue"),
        expected_data={"test": "testValue"},
    )


def test_evaluates_methods():
    class Adder:
        def __init__(self, value):
            self._num = value

        def test(self, ctx, *_, addend1):
            return self._num + addend1 + ctx["addend2"]

    schema = create_test_schema(Field("test", Int, [Argument("addend1", Int)]))
    root = Adder(700)

    assert_sync_execution(
        schema,
        "{ test(addend1: 80) }",
        initial_value=root,
        context_value={"addend2": 9},
        expected_data={"test": 789},
    )


def test_evaluates_callables():
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
