# -*- coding: utf-8 -*-
""" execution tests related to list types handling and resolution """

import pytest

from py_gql._utils import deduplicate, lazy
from py_gql.schema import (
    Field,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
)

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def run_test(
    test_type,
    test_data,
    *,
    assert_execution,
    expected_data=None,
    expected_errors=None,
    expected_exc=None,
    expected_msg=None
):

    data = {"test": test_data}
    data_type = ObjectType(
        "DataType",
        [
            Field("test", test_type),
            Field("nest", lambda: data_type, resolver=lambda *_: data),
        ],
    )  # type: ObjectType
    schema = Schema(data_type)

    await assert_execution(
        schema,
        "{ nest { test } }",
        initial_value=data,
        expected_data=(
            {"nest": {"test": expected_data}}
            if expected_data is not None
            else None
        ),
        expected_errors=expected_errors,
        expected_exc=(expected_exc, expected_msg),
    )


def _generator(iterable):
    for entry in iterable:
        yield entry


# Python sets are not ordered so here's a dumb iterable implementation
def _sortedset(values):
    return list(deduplicate(values))


def _lazy(values):
    return lambda *a, **kw: values


_FRUITS = ["apple", "banana", "apple", "coconut"]


@pytest.mark.parametrize(
    "iterable,result",
    [
        (_FRUITS, _FRUITS),
        (_sortedset(_FRUITS), ["apple", "banana", "coconut"]),
        (lambda: _generator(_FRUITS), _FRUITS),
    ],
)
async def test_it_accepts_iterables_for_list_type(
    assert_execution, iterable, result
):
    await run_test(
        ListType(String),
        lazy(iterable),
        expected_data=result,
        assert_execution=assert_execution,
    )


@pytest.mark.parametrize("not_iterable", ["apple", 42, object()])
async def test_it_raises_on_non_iterable_value_for_list_type(
    assert_execution, not_iterable
):
    await run_test(
        ListType(String),
        not_iterable,
        assert_execution=assert_execution,
        expected_exc=RuntimeError,
        expected_msg=(
            'Field "nest.test" is a list type and resolved value should '
            "be iterable"
        ),
    )


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param([1, 2], [1, 2], id="[T]"),
        pytest.param([1, None, 2], [1, None, 2], id="[T], contains null"),
        pytest.param(_lazy([1, 2]), [1, 2], id="[T], callable"),
        pytest.param(
            _lazy([1, None, 2]), [1, None, 2], id="[T], callable, contains null"
        ),
        pytest.param(None, None, id="[T], null"),
        pytest.param(_lazy(None), None, id="[T], callable, null"),
    ],
)
async def test_nullable_list_of_nullable_items(
    assert_execution, data, expected
):
    await run_test(
        ListType(Int),
        data,
        expected_data=expected,
        assert_execution=assert_execution,
    )


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param([1, 2], [1, 2], id="[T]!"),
        pytest.param([1, None, 2], [1, None, 2], id="[T]!, contains null"),
        pytest.param(_lazy([1, 2]), [1, 2], id="[T]!, callable"),
        pytest.param(
            _lazy([1, None, 2]),
            [1, None, 2],
            id="[T]!, callable, contains null",
        ),
    ],
)
async def test_non_nullable_list_of_nullable_items_ok(
    assert_execution, data, expected
):
    await run_test(
        NonNullType(ListType(Int)),
        data,
        expected_data=expected,
        assert_execution=assert_execution,
    )


@pytest.mark.parametrize(
    "data, expected_err",
    [
        (None, ('Field "nest.test" is not nullable', (9, 13), "nest.test")),
        (
            _lazy(None),
            ('Field "nest.test" is not nullable', (9, 13), "nest.test"),
        ),
    ],
)
async def test_non_nullable_list_of_nullable_items_fail(
    assert_execution, data, expected_err
):
    await run_test(
        NonNullType(ListType(Int)),
        data,
        expected_errors=[expected_err],
        assert_execution=assert_execution,
    )


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param([1, 2], [1, 2], id="[T!]"),
        pytest.param(_lazy([1, 2]), [1, 2], id="[T!], callable"),
        pytest.param(None, None, id="[T!], null"),
        pytest.param(_lazy(None), None, id="[T!], callable, null"),
    ],
)
async def test_nullable_list_of_non_nullable_items_ok(
    assert_execution, data, expected
):
    await run_test(
        ListType(NonNullType(Int)),
        data,
        expected_data=expected,
        assert_execution=assert_execution,
    )


@pytest.mark.parametrize(
    "data, expected_err",
    [
        (
            [1, None, 2],
            ('Field "nest.test[1]" is not nullable', (9, 13), "nest.test[1]"),
        ),
        (
            _lazy([1, None, 2]),
            ('Field "nest.test[1]" is not nullable', (9, 13), "nest.test[1]"),
        ),
    ],
)
async def test_nullable_list_of_non_nullable_items_fail(
    assert_execution, data, expected_err
):
    await run_test(
        ListType(NonNullType(Int)),
        data,
        expected_errors=[expected_err],
        assert_execution=assert_execution,
    )
