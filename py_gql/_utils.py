# -*- coding: utf-8 -*-
""" Some generic laguage level utilities for internal use. """

import collections
import sys
from asyncio import gather
from inspect import isawaitable
from typing import (
    AbstractSet,
    Any,
    Awaitable,
    Callable,
    Dict,
    Hashable,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    ValuesView,
    cast,
)

T = TypeVar("T")
G = TypeVar("G")
H = TypeVar("H", bound=Hashable)

Lazy = Union[T, Callable[[], T]]
MaybeAwaitable = Union[Awaitable[T], T]


def lazy(maybe_callable: Union[T, Callable[[], T]]) -> T:
    """ Calls a value if callable else returns it.

    >>> lazy(42)
    42

    >>> lazy(lambda: 42)
    42
    """
    if callable(maybe_callable):
        return maybe_callable()
    return maybe_callable


_MISSING = object()


def deduplicate(
    iterable: Iterable[H], key: Optional[Callable[[H], Hashable]] = None
) -> Iterator[H]:
    """ Deduplicate an iterable.

    Args:
        iterable (Iterator[any]): source iterator
        key (Callable): Identity function

    Yields:
        any: next deduplicated entry in order of original appearance

    >>> list(deduplicate([1, 2, 1, 3, 3]))
    [1, 2, 3]

    >>> list(deduplicate([1, 2, 1, 3, 3], key=lambda x: x % 2))
    [1, 2]
    """
    seen = set()  # type: Set[Hashable]

    keyed = (
        ((entry, entry) for entry in iterable)
        if key is None
        else ((entry, key(entry)) for entry in iterable)
    )  # type: Iterator[Tuple[H, Hashable]]

    for entry, key_ in keyed:
        if key_ in seen:
            continue
        seen.add(key_)
        yield entry


def maybe_first(
    iterable: Iterable[T], default: Optional[T] = None
) -> Optional[T]:
    """ Return the first item in an iterable or None.

    >>> maybe_first([1, 2, 3])
    1

    >>> maybe_first(()) is None
    True

    >>> maybe_first((), 1)
    1
    """
    try:
        return next(iter(iterable))
    except StopIteration:
        return default


def find_one(
    iterable: Iterable[T],
    predicate: Callable[[T], Any],
    default: Optional[T] = None,
) -> Optional[T]:
    """ Extract first item matching a predicate function in an iterable.
    Returns ``None`` if no entry is found.

    >>> find_one([1, 2, 3, 4], lambda x: x == 2)
    2

    >>> find_one([1, 2, 3, 4], lambda x: x == 5) is None
    True
    """
    return maybe_first(
        (entry for entry in iterable if predicate(entry)), default=default
    )


# TODO: Not sure how to type this correctly without recursive types.
def flatten(lst):
    """ Recursive flatten (list, tuple) of potentially (lists, tuples)
    `itertools.chain` could be used instead but would flatten all iterables
    including strings which is not ideal.

    >>> list(flatten([1, 2, (1, 2, [3])]))
    [1, 2, 1, 2, 3]

    >>> list(flatten([]))
    []

    >>> list(flatten([[], []]))
    []
    """
    for entry in lst:
        if type(entry) in (list, tuple):
            for subentry in flatten(entry):
                yield subentry
        else:
            yield entry


def is_iterable(value: Any, strings: bool = True) -> bool:
    """ Check if a value is iterable.

    This does no type comparisons.
    Note that by default strings are iterables too!

    Args:
        value (any): Maybe iterable
        strings (bool): Include strings as iterable, defaults to ``True``

    Returns:
        bool: Whether ``value`` is iterable

    >>> is_iterable([])
    True

    >>> is_iterable((x for x in range(10)))
    True

    >>> is_iterable("Hello World!")
    True

    >>> is_iterable("Hello World!", False)
    False

    >>> is_iterable(False)
    False
    """
    try:
        iter(value)
    except TypeError:
        return False
    else:
        return strings or not isinstance(value, (str, bytes))


def nested_key(
    obj: Mapping[str, Any], *keys: str, default: Any = _MISSING
) -> Any:
    """ Safely extract nested key from dicts and lists.

    >>> source = {'foo': {'bar': [{}, {}, {'baz': 42}]}}

    >>> nested_key(source, 'foo', 'bar', 2, 'baz')
    42

    >>> nested_key(source, 'foo', 'bar', 10, 'baz')
    Traceback (most recent call last):
        ...
    IndexError: list index out of range

    >>> nested_key(source, 'foo', 'bar', 10, 'baz', default=None) is None
    True

    >>> nested_key(source, 'foo', 'baz', default=None) is None
    True

    """
    for key in keys:
        try:
            obj = obj[key]
        except (KeyError, IndexError):
            if default is _MISSING:
                raise
            return default
    return obj


def deferred_apply(
    value: MaybeAwaitable[T], func: Callable[[T], G]
) -> MaybeAwaitable[G]:
    """ Apply a transformation to a value which can be deferred or not.

    If the value is deferred (respectively not deferred) the result of this
    function is deferred (respectively not deferred).
    """
    if isawaitable(value):

        async def deferred() -> G:
            return func(await cast(Awaitable[T], value))

        return deferred()
    return func(cast(T, value))


def deferred_list(
    source: Iterable[MaybeAwaitable[T]]
) -> MaybeAwaitable[List[T]]:
    """ Transform an iterator of deferred values into a deferred iterator.

    If no value in the source iterator is deferred, the result is not deferred,
    while if any value is deferred then the result is deferred.
    """
    deferred = []  # type: List[int]
    results = []  # type: List[MaybeAwaitable[T]]

    for index, value in enumerate(source):
        if isawaitable(value):
            deferred.append(index)
        results.append(value)

    if not deferred:
        return cast(List[T], results)

    async def deferred_result() -> List[T]:
        awaited = await gather(
            *(cast(Awaitable[T], results[index]) for index in deferred)
        )
        for index, result in zip(deferred, awaited):
            results[index] = result
        return cast(List[T], results)

    return deferred_result()


def deferred_dict(
    source: Iterable[Tuple[str, MaybeAwaitable[T]]]
) -> MaybeAwaitable[Dict[str, T]]:
    """ Transform an iterator of keys and deferred values into a deferred dict.

    If no value in the source iterator is deferred, the result is not deferred,
    while if any value is deferred then the result is deferred.
    """
    deferred = []  # type: List[str]
    target = {}  # type: Dict[str, MaybeAwaitable[T]]

    for key, value in source:
        if isawaitable(value):
            deferred.append(key)
        target[key] = value

    if not deferred:
        return cast(Dict[str, T], target)

    async def deferred_result() -> Dict[str, T]:
        awaited = await gather(
            *(cast(Awaitable[T], target[key]) for key in deferred)
        )
        for key, result in zip(deferred, awaited):
            target[key] = result

        return cast(Dict[str, T], target)

    return deferred_result()


async def ensure_deferred(value: MaybeAwaitable[T]) -> T:
    return (
        (await cast(Awaitable[T], value))
        if isawaitable(value)
        else cast(T, value)
    )


def deferred_serial(
    steps: List[Callable[[], MaybeAwaitable[T]]]
) -> MaybeAwaitable[List[T]]:
    """ Runs a series of function in a serial manner, unwrapping coroutines
    along the way. """
    steps = list(steps)[::-1]
    results = []  # type: List[T]

    def _next() -> MaybeAwaitable[List[T]]:
        try:
            result = steps.pop()()
        except IndexError:
            return results
        else:
            if isawaitable(result):

                async def deferred() -> List[T]:
                    inner = await cast(Awaitable[T], result)
                    results.append(inner)
                    return await ensure_deferred(_next())

                return deferred()

            else:
                results.append(cast(T, result))
                return _next()

    return _next()


if sys.version < "3.6":  # noqa: C901
    OrderedDict = collections.OrderedDict

    K = TypeVar("K")
    V = TypeVar("V")

    # TODO: There is most certainly a more terse implementation but inherinting
    # from OrderedDict doesn't seem to play nice with mypy.
    class DefaultOrderedDict(MutableMapping[K, V]):

        __slots__ = ("_inner", "default_factory")

        def __init__(
            self, default_factory: Callable[[], V], *args: Any, **kwargs: Any
        ):
            if default_factory is not None and not callable(default_factory):
                raise TypeError("default_factory must be callable")

            self.default_factory = default_factory
            self._inner = OrderedDict()  # type: MutableMapping[K, V]

        def __getitem__(self, key: K) -> V:
            try:
                return self._inner[key]
            except KeyError:
                return self.__missing__(key)

        def __missing__(self, key: K) -> V:
            if self.default_factory is None:
                raise KeyError(key)

            self._inner[key] = value = self.default_factory()
            return value

        def __len__(self):
            return len(self._inner)

        def __setitem__(self, key: K, value: V) -> None:
            self._inner[key] = value

        def __delitem__(self, key: K) -> None:
            del self._inner[key]

        def __iter__(self) -> Iterator[K]:
            return iter(self._inner)

        def clear(self) -> None:
            self._inner.clear()

        def keys(self) -> AbstractSet[K]:
            return self._inner.keys()

        def values(self) -> ValuesView[V]:
            return self._inner.values()

        def items(self) -> AbstractSet[Tuple[K, V]]:
            return self._inner.items()

        def pop(self, key: K, **kwargs: Any) -> V:  # type: ignore
            return self._inner.pop(key, **kwargs)

        def __contains__(self, key: Any) -> bool:
            return key in self._inner

        def __bool__(self) -> bool:
            return bool(self._inner)


else:
    OrderedDict = dict  # type: ignore
    DefaultOrderedDict = collections.defaultdict  # type: ignore
