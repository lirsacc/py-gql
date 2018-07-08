# -*- coding: utf-8 -*-
""" Some generic laguage level utilities for internal use. """

import collections
import functools as ft
import sys

import six


def lazy(maybe_callable):
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


class cached_property(property):
    """ Decorator that converts a method into a lazy property.
    The method behaves like a regular ``@property`` except that it
    is called only once.

    **Warning** This requires the class to have a ``__dict__`` attribute,
    so no class using __slots__.
    """

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _MISSING)
        if value is _MISSING:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def deduplicate(iterable, key=None):
    """ Deduplicate an iterable.

    Args:
        iterable (Iterator[any]): source iterator
        key (callable): Identity function

    Yields:
        any: next deduplicated entry in order of original appearance

    >>> list(deduplicate([1, 2, 1, 3, 3]))
    [1, 2, 3]

    >>> list(deduplicate([1, 2, 1, 3, 3], key=lambda x: x % 2))
    [1, 2]
    """
    if key is None:

        def key(x):
            return x

    seen = set()

    for entry in iterable:
        key_ = key(entry)
        if key_ in seen:
            continue
        seen.add(key_)
        yield entry


def maybe_first(iterable, default=None):
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


def find_one(iterable, predicate, default=None):
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


if sys.version >= "3.7":  # flake8: noqa
    # Take advantage that dicts are guaranteed ordered from 3.7 onward
    OrderedDict = dict
    DefaultOrderedDict = collections.defaultdict
else:
    OrderedDict = collections.OrderedDict

    # Source: http://stackoverflow.com/a/6190500/562769
    class DefaultOrderedDict(OrderedDict):
        def __init__(self, default_factory=None, *a, **kw):
            if default_factory is not None and not callable(default_factory):
                raise TypeError("first argument must be callable")
            OrderedDict.__init__(self, *a, **kw)
            self.default_factory = default_factory

        def __getitem__(self, key):
            try:
                return OrderedDict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)

        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value

        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = (self.default_factory,)
            return type(self), args, None, None, self.items()

        def copy(self):
            return self.__copy__()

        def __copy__(self):
            return type(self)(self.default_factory, self)

        def __deepcopy__(self, memo):
            import copy

            return type(self)(self.default_factory, copy.deepcopy(self.items()))

        def __repr__(self):
            return "DefaultOrderedDict(%s, %s)" % (
                self.default_factory,
                OrderedDict.__repr__(self),
            )


def flatten(lst):
    """ Recursive flatten (list, tuple) of potentially (lists, tuples)
    `itertools.chain` could be used instead but would flatten all iterables
    including strings which is not ideal.

    >>> list(flatten([1, 2, (1, 2, [3])]))
    [1, 2, 1, 2, 3]
    """
    for entry in lst:
        if isinstance(entry, (list, tuple)):
            for subentry in flatten(entry):
                yield subentry
        else:
            yield entry


def is_iterable(value, strings=True):
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
        return strings or not isinstance(value, six.string_types)


def nested_key(obj, *keys, **kwargs):
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
    default = kwargs.get("default", _MISSING)
    for key in keys:
        try:
            obj = obj[key]
        except (KeyError, IndexError):
            if default is _MISSING:
                raise
            return default
    return obj
