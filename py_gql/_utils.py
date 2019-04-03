# -*- coding: utf-8 -*-
""" Some generic laguage level utilities for internal use. """

import collections
import sys
from typing import (
    AbstractSet,
    Any,
    Callable,
    Hashable,
    Iterable,
    Iterator,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    ValuesView,
)

T = TypeVar("T")
G = TypeVar("G")
H = TypeVar("H", bound=Hashable)

Lazy = Union[T, Callable[[], T]]


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


def map_and_filter(
    func: Callable[[T], Optional[T]], iterator: Iterable[T]
) -> Iterator[T]:
    """ Map an  iterable filtering out None.

    >>> list(map_and_filter(lambda x: None if x % 2 else x, range(10)))
    [0, 2, 4, 6, 8]
    """
    for entry in iterator:
        mapped = func(entry)
        if mapped is not None:
            yield mapped


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
