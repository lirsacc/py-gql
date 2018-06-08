# -*- coding: utf-8 -*-
""" Some generic laguage level utilities. """

import collections as _collections
import contextlib as _contextlib
import sys as _sys
import six as _six


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


MISSING = object()


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
        value = obj.__dict__.get(self.__name__, MISSING)
        if value is MISSING:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def deduplicate(iterable, key=None):
    """ Deduplicate an iterable.

    [WARN] The return type is a generator and can only be consumed once,
    wrap with `list` if you need a static result.

    :type iterable: Iterable
    :param iterable: Source iterable.

    :type key: Optional[callable]
    :param key: Key used to identify equal entries.

    :type: Iterable

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


def find_one(iterable, predicate):
    """ Extract first item matching a predicate function in an iterable.

    Returns None if no entry is found. Basically a shortcut for ``maybe_first``
    when extracting based on a predicate.

    >>> find_one([1, 2, 3, 4], lambda x: x == 2)
    2

    >>> find_one([1, 2, 3, 4], lambda x: x == 5) is None
    True
    """
    return maybe_first((entry for entry in iterable if predicate(entry)), None)


if _sys.version >= '3.7':  # flake8: noqa
    # Take advantage that dicts are guaranteed ordred from 3.7 onward
    OrderedDict = dict
    DefaultOrderedDict = _collections.defaultdict
else:
    OrderedDict = _collections.OrderedDict

    class DefaultOrderedDict(OrderedDict):
        """ OrderedDict with default values """
        # Source: http://stackoverflow.com/a/6190500/562769
        def __init__(self, default_factory=None, *a, **kw):
            if default_factory is not None and not callable(default_factory):
                raise TypeError('first argument must be callable')
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
                args = self.default_factory,
            return type(self), args, None, None, self.items()

        def copy(self):
            return self.__copy__()

        def __copy__(self):
            return type(self)(self.default_factory, self)

        def __deepcopy__(self, memo):
            import copy
            return type(self)(
                self.default_factory,
                copy.deepcopy(self.items())
            )

        def __repr__(self):
            return 'OrderedDefaultDict(%s, %s)' % (
                self.default_factory,
                OrderedDict.__repr__(self)
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

    >>> is_iterable([])
    True

    >>> is_iterable("Hello World!")
    True

    >>> is_iterable("Hello World!", False)
    False

    >>> is_iterable(False)
    False

    :type value: any
    :param value:
        Object to inspect

    :type strings: bool
    :param strings:
        Are strings allowed as iterators?

    :rtype: bool
    """
    try:
        iter(value)
    except TypeError:
        return False
    else:
        return strings or not isinstance(value, _six.string_types)


class Path(object):
    """ Helper class to manage paths into nested structures.

    Mostly compatible with lists and / or strings.

    >>> Path(['foo', 0, 'bar'])
    <Path foo[0].bar>

    >>> list(Path(['foo', 0, 'bar']))
    ['foo', 0, 'bar']
    """

    __slots__ = ('_entries')

    def __init__(self, entries=None):
        self._entries = list(entries) if entries is not None else []

    def __add__(self, other_path):
        """
        >>> Path(['foo', 0, 'bar']) + 'baz'
        <Path foo[0].bar.baz>

        >>> Path(['foo', 0, 'bar']) + 1
        <Path foo[0].bar[1]>

        >>> Path(['foo', 0, 'bar']) + Path(['baz', 1])
        <Path foo[0].bar.baz[1]>

        >>> Path(['foo', 0, 'bar']) + ['baz', 1]
        <Path foo[0].bar.baz[1]>
        """
        if isinstance(other_path, (_six.string_types, int)):
            return self.__class__(self._entries + [other_path])
        elif isinstance(other_path, list):
            return self.__class__(self._entries + other_path)
        elif isinstance(other_path, Path):
            return self.__class__(self._entries + other_path._entries)
        else:
            raise TypeError()

    def __str__(self):
        """
        >>> str(Path(['foo', 0, 'bar']))
        'foo[0].bar'
        """
        path_str = ''
        for entry in self._entries:
            if isinstance(entry, int):
                path_str += "[%s]" % entry
            else:
                path_str += ".%s" % entry
        return path_str.lstrip('.')

    def __repr__(self):
        if not self._entries:
            return '<%s empty>' % (self.__class__.__name__)
        return '<%s %s>' % (self.__class__.__name__, self)

    def __eq__(self, lhs):
        """
        >>> Path(['foo', 0, 'bar']) == ['foo', 0, 'bar']
        True

        >>> Path(['foo', 0, 'bar']) == 'foo[0].bar'
        True

        >>> Path(['foo', 0, 'bar']) == Path(['foo', 0, 'bar'])
        True
        """
        if isinstance(lhs, list):
            return self._entries == lhs
        if isinstance(lhs, _six.string_types):
            return str(self) == lhs
        elif isinstance(lhs, Path):
            return self._entries == lhs._entries
        else:
            raise TypeError()

    def __getitem__(self, index):
        """
        >>> Path(['foo', 0, 'bar'])[0]
        'foo'

        >>> Path(['foo', 0, 'bar'])[1]
        0

        >>> Path(['foo', 0, 'bar'])[10]
        Traceback (most recent call last):
            ...
        IndexError: list index out of range
        """
        return self._entries[index]

    def __bool__(self):
        """
        >>> bool(Path())
        False

        >>> bool(Path(['foo']))
        True
        """
        return bool(self._entries)

    __nonzero__ = __bool__


@_contextlib.contextmanager
def capture_exceptions(cls, cb=None):
    """ Capture all exception

    Args:
        cls (type|tuple[type]): Exception class(es) to ignore
        cb (callable, optional): Optional processor for the capture exceptions

    Usage:

        >>> capture = []
        >>> with capture_exceptions(ValueError, capture.append):
        ...     int('not int')
        >>> capture
        [ValueError("invalid literal for int() with base 10: 'not int'",)]

        >>> with capture_exceptions(ValueError):
        ...     int('not int')

    """
    try:
        yield
    except cls as err:
        if callable(cb):
            cb(err)
