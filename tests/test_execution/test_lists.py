# -*- coding: utf-8 -*-
""" execution tests related to list types handling and resolution """

import pytest

from py_gql._utils import deduplicate
from py_gql.schema import (
    Field,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
)

from ._test_utils import check_execution


def run_test(
    test_type,
    test_data,
    expected_data=None,
    expected_errors=None,
    expected_exc=None,
    expected_msg=None,
):

    data = {"test": test_data}
    data_type = ObjectType(
        "DataType",
        [
            Field("test", test_type),
            Field("nest", lambda: data_type, resolve=lambda *_: data),
        ],
    )
    schema = Schema(data_type)
    "{ nest { test } }"

    check_execution(
        schema,
        "{ nest { test } }",
        initial_value=data,
        expected_data={"nest": {"test": expected_data}}
        if expected_data is not None
        else None,
        expected_errors=expected_errors,
        expected_exc=expected_exc,
        expected_msg=expected_msg,
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
        (_generator(_FRUITS), _FRUITS),
    ],
)
def test_it_accepts_iterables_for_list_type(iterable, result):
    run_test(ListType(String), iterable, result, [])


@pytest.mark.parametrize("not_iterable", ["apple", 42, object()])
def test_it_raises_on_non_iterable_value_for_list_type(not_iterable):
    run_test(
        ListType(String),
        not_iterable,
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
def test_nullable_list_of_nullable_items(data, expected):
    run_test(ListType(Int), data, expected)


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
def test_non_nullable_list_of_nullable_items_ok(data, expected):
    run_test(NonNullType(ListType(Int)), data, expected)


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
def test_non_nullable_list_of_nullable_items_fail(data, expected_err):
    run_test(NonNullType(ListType(Int)), data, None, [expected_err])


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param([1, 2], [1, 2], id="[T!]"),
        pytest.param(_lazy([1, 2]), [1, 2], id="[T!], callable"),
        pytest.param(None, None, id="[T!], null"),
        pytest.param(_lazy(None), None, id="[T!], callable, null"),
    ],
)
def test_nullable_list_of_non_nullable_items_ok(data, expected):
    run_test(ListType(NonNullType(Int)), data, expected)


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
def test_nullable_list_of_non_nullable_items_fail(data, expected_err):
    run_test(ListType(NonNullType(Int)), data, None, [expected_err])
