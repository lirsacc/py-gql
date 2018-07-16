# -*- coding: utf-8 -*-

from concurrent import futures as _f

import pytest

from py_gql.execution import _concurrency


def test_all_wrapper_sync():
    futures = [x for x in range(10)]
    wrapper = _concurrency.all_(futures)
    assert wrapper == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_all_wrapper_futures_ok():
    futures = [_f.Future() for _ in range(10)]

    wrapper = _concurrency.all_(futures)
    for i, f in enumerate(futures):
        f.set_result(i)

    assert wrapper.result() == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_all_wrapper_futures_mixed():
    futures = []

    for x in range(10):
        if x % 2:
            f = _f.Future()
            futures.append(f)
        else:
            futures.append(x)

    wrapper = _concurrency.all_(futures)
    for i, f in enumerate(futures):
        if i % 2:
            f.set_result(i)

    assert wrapper.result() == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_all_wrapper_partially_completed():
    futures = [_f.Future() for _ in range(10)]

    for i, f in enumerate(futures):
        if i % 2:
            f.set_result(i)

    wrapper = _concurrency.all_(futures)

    for i, f in enumerate(futures):
        if not i % 2:
            f.set_result(i)

    assert wrapper.result() == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_all_wrapper_one_future_fails():
    futures = [_f.Future() for _ in range(10)]
    for i, f in enumerate(futures):
        if i == 9:
            f.set_exception(ValueError("I don't like 9"))
        else:
            f.set_result(i)

    wrapper = _concurrency.all_(futures)

    with pytest.raises(ValueError) as exc_info:
        wrapper.result()

    assert str(exc_info.value) == "I don't like 9"


def test_chain_wrapper_sync_steps():
    f = _f.Future()
    c = _concurrency.chain(f, lambda x: x + 1, lambda x: x * 2)
    f.set_result(1)
    assert c.result() == 4


def test_chain_wrapper_sync_failure():
    f = _f.Future()

    def _bad_step(x):
        raise ValueError(x)

    c = _concurrency.chain(f, _bad_step)
    f.set_result(1)

    with pytest.raises(ValueError) as exc_info:
        c.result(timeout=1)

    assert str(exc_info.value) == "1"


def test_chain_wrapper_async_step():
    with _f.ThreadPoolExecutor(max_workers=1) as executor:

        def sync_step(x):
            return x * 2

        def async_step(x):
            return executor.submit(sync_step, x)

        c = _concurrency.chain(1, lambda x: x + 1, async_step, lambda x: x + 1)
        assert c.result() == 5


def test_chain_wrapper_async_failure():
    with _f.ThreadPoolExecutor(max_workers=1) as executor:

        def sync_step(x):
            raise ValueError(x)

        def async_step(x):
            return executor.submit(sync_step, x)

        c = _concurrency.chain(1, lambda x: x + 1, async_step, lambda x: x + 1)
        with pytest.raises(ValueError) as exc_info:
            c.result()

        assert str(exc_info.value) == "2"


def test_serial_ok_sync():

    called = []

    def make_step(x):
        def _step():
            assert called == list(range(x))
            called.append(x)

        return _step

    assert _concurrency.serial([make_step(x) for x in range(10)]) is None
    assert called == list(range(10))


def test_serial_ok_async():

    called = []

    def make_step(x):
        def _step():
            assert called == list(range(x))
            f = _f.Future()
            f.set_result(x)
            called.append(x)
            return f

        return _step

    assert _concurrency.serial([make_step(x) for x in range(10)]).result()
    assert called == list(range(10))


def test_unwrap_ok():
    futures = [_f.Future() for _ in range(10)]
    futures[-1].set_result("final")
    for i, f in enumerate(futures[:-1]):
        f.set_result(futures[i + 1])

    assert _concurrency.unwrap(futures[0]).result() == "final"


def test_unwrap_intermediate_failure():
    futures = [_f.Future() for _ in range(10)]
    futures[-1].set_result("final")
    for i, f in enumerate(futures[:-1]):
        if i != 5:
            f.set_result(futures[i + 1])
        else:
            f.set_exception(ValueError(5))

    with pytest.raises(ValueError) as exc_info:
        _concurrency.unwrap(futures[0]).result()

    assert str(exc_info.value) == "5"


def test_unwrap_intermediate_cancel():
    futures = [_f.Future() for _ in range(10)]
    futures[-1].set_result("final")
    for i, f in enumerate(futures[:-1]):
        if i != 5:
            f.set_result(futures[i + 1])
        else:
            f.cancel()

    with pytest.raises(_f.CancelledError):
        _concurrency.unwrap(futures[0]).result()


def test_except_wrapper():
    f = _f.Future()
    e = _concurrency.except_(f)
    f.set_exception(ValueError("foo"))
    assert e.result() is None


def test_except_wrapper_with_mapper():
    f = _f.Future()
    e = _concurrency.except_(f, map_=str)
    f.set_exception(ValueError("foo"))
    assert e.result() == "foo"


def test_except_wrapper_correct_exc_cls():
    f = _f.Future()
    e = _concurrency.except_(f, (ValueError,))
    f.set_exception(ValueError("foo"))
    assert e.result() is None


def test_except_wrapper_incorrect_exc_cls():
    f = _f.Future()
    e = _concurrency.except_(f, (TypeError,))
    f.set_exception(ValueError("foo"))

    with pytest.raises(ValueError):
        e.result()
