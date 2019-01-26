# -*- coding: utf-8 -*-
""" """

import pytest

from py_gql._utils import (
    deferred_apply,
    deferred_dict,
    deferred_list,
    deferred_serial,
)


async def _deferred(x):
    return x


def test_deferred_apply_sync():
    assert 43 == deferred_apply(42, lambda x: x + 1)


@pytest.mark.asyncio
async def test_deferred_apply_async():
    value = deferred_apply(_deferred(42), lambda x: x + 1)  # type: ignore
    assert 43 == await value


def test_deferred_list_empty():
    assert [] == deferred_list([])


def test_deferred_list_all_sync():
    assert [1, 2, 3, 4] == deferred_list([1, 2, 3, 4])


@pytest.mark.asyncio
async def test_deferred_list_all_async():

    assert [1, 2, 3, 4] == await deferred_list(  # type: ignore
        [_deferred(x) for x in (1, 2, 3, 4)]
    )


@pytest.mark.asyncio
async def test_deferred_list_mixed():

    assert [1, 2, 3, 4] == await deferred_list(  # type: ignore
        [1, 2, _deferred(3), 4]
    )


def test_deferred_dict_empty():
    assert {} == deferred_dict(())


def test_deferred_dict_all_sync():
    assert dict(one=1, two=2, three=3) == deferred_dict(
        dict(one=1, two=2, three=3).items()
    )


@pytest.mark.asyncio
async def test_deferred_dict_all_async():
    assert dict(one=1, two=2, three=3) == await deferred_dict(  # type: ignore
        dict(one=_deferred(1), two=_deferred(2), three=_deferred(3)).items()
    )


@pytest.mark.asyncio
async def test_deferred_dict_mixed():

    assert dict(one=1, two=2, three=3) == await deferred_dict(  # type: ignore
        dict(one=_deferred(1), two=2, three=_deferred(3)).items()
    )


def test_deferred_serial_empty():
    assert [] == deferred_serial([])  # type: ignore


def test_deferred_serial_all_sync():

    called = []  # type: ignore

    def make_step(x):
        def _step():
            assert called == list(range(x))
            called.append(x)
            return x

        return _step

    assert [0, 1, 2, 3, 4] == deferred_serial(
        [make_step(0), make_step(1), make_step(2), make_step(3), make_step(4)]
    )

    assert [0, 1, 2, 3, 4] == called


@pytest.mark.asyncio
async def test_deferred_serial_all_async():

    called = []  # type: ignore

    def make_step(x):
        def _step():
            assert called == list(range(x))
            called.append(x)
            return _deferred(x)

        return _step

    assert [0, 1, 2, 3, 4] == await deferred_serial(  # type: ignore
        [make_step(0), make_step(1), make_step(2), make_step(3), make_step(4)]
    )

    assert [0, 1, 2, 3, 4] == called


@pytest.mark.asyncio
async def test_deferred_serial_mixed():

    called = []  # type: ignore

    def make_step(x):
        def _step():
            assert called == list(range(x))
            called.append(x)
            return _deferred(x) if x % 2 else x

        return _step

    assert [0, 1, 2, 3, 4] == await deferred_serial(  # type: ignore
        [make_step(0), make_step(1), make_step(2), make_step(3), make_step(4)]
    )

    assert [0, 1, 2, 3, 4] == called
