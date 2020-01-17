# -*- coding: utf-8 -*-
""" Some generic laguage level utilities for internal use. """

import collections
import functools
import sys
import warnings
from typing import (
    AbstractSet,
    Any,
    Callable,
    Hashable,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    ValuesView,
    cast,
)

T = TypeVar("T")
G = TypeVar("G")
H = TypeVar("H", bound=Hashable)
C = TypeVar("C", bound=Callable[..., T])
FuncType = Callable[..., Any]
Fn = TypeVar("Fn", bound=FuncType)
TType = TypeVar("TType", bound=Type[Any])

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
    func: Callable[[T], Optional[T]], iterable: Iterable[T]
) -> List[T]:
    """ Map an  iterable filtering out None.

    >>> map_and_filter(lambda x: None if x % 2 else x, range(10))
    [0, 2, 4, 6, 8]
    """
    return [m for m in (func(e) for e in iterable) if m is not None]


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


def classdispatch(
    value: Any, registry: Mapping[TType, C], *args: Any, **kwargs: Any
) -> T:
    """
    Poor man's singledispatch to be used inline.

    >>> class A:
    ...     pass

    >>> class B(A):
    ...     pass

    >>> class C(A):
    ...     pass

    >>> registry = {A: lambda _: 1, B: lambda _: 2}

    >>> classdispatch(A(), registry)
    1

    >>> classdispatch(B(), registry)
    2

    >>> classdispatch(C(), registry)
    Traceback (most recent call last):
        ...
    TypeError: <class 'py_gql._utils.C'>

    >>> classdispatch(object(), registry)
    Traceback (most recent call last):
        ...
    TypeError: <class 'object'>

    >>> classdispatch(A(), {
    ...     A: lambda _, *a, **kw: (a, sorted(kw.items()))
    ... }, 0, 1, foo=2, bar=3)
    ((0, 1), [('bar', 3), ('foo', 2)])
    """
    try:
        impl = registry[value.__class__]
    except KeyError:
        raise TypeError(value.__class__)

    return impl(value, *args, **kwargs)


def apply_middlewares(
    func: Callable[..., Any], middlewares: Sequence[Callable[..., Any]]
) -> Callable[..., Any]:
    """Apply a list of middlewares to a source function.

    - Middlewares must be structured as: ``middleware(next, *args, **kwargs)``
      and call the next middleware inline.

    >>> def square(x): return x ** 2
    >>> def double(next, x): return next(x * 2)
    >>> def substract_one(next, x): return next(x - 1)

    >>> final = apply_middlewares(square, [double, substract_one])

    >>> final(2)  # ((2 - 1) * 2) ^ 2
    4

    >>> final(10)  # ((10 - 1) * 2) ^ 2
    324
    """
    tail = func
    for mw in middlewares:
        if not callable(mw):
            raise TypeError("Middleware should be a callable")

        tail = functools.partial(mw, tail)

    return tail


def deprecated(reason: str) -> Callable[[Fn], Fn]:
    def decorator(fn: Fn) -> Fn:
        @functools.wraps
        def deprecated_fn(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.simplefilter("always", DeprecationWarning)
                warnings.warn(reason, category=DeprecationWarning, stacklevel=2)
            return fn(*args, **kwargs)

        return cast(Fn, deprecated_fn)

    return decorator
