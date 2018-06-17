# -*- coding: utf-8 -*-
""" """

import six


class Path(object):
    """ Helper class to encode traversal paths into nested structures.

    You can interact with it naturally with list, strings or integers (treated as
    list indices)

    >>> Path(['foo', 0, 'bar'])
    <Path foo[0].bar>

    >>> Path()
    <Path empty>

    >>> list(Path(['foo', 0, 'bar']))
    ['foo', 0, 'bar']

    >>> str(Path() + 'foo' + 1 + 'bar')
    'foo[1].bar'
    """

    __slots__ = "_entries"

    def __init__(self, entries=None):
        self._entries = list(entries) if entries is not None else []

    def __add__(self, other):
        """
        >>> Path(['foo', 0, 'bar']) + 'baz'
        <Path foo[0].bar.baz>

        >>> Path(['foo', 0, 'bar']) + 1
        <Path foo[0].bar[1]>

        >>> Path(['foo', 0, 'bar']) + Path(['baz', 1])
        <Path foo[0].bar.baz[1]>

        >>> Path(['foo', 0, 'bar']) + ['baz', 1]
        <Path foo[0].bar.baz[1]>

        >>> Path() + object()
        Traceback (most recent call last):
            ...
        TypeError
        """
        if isinstance(other, (six.string_types, int)):
            return self.__class__(self._entries + [other])
        elif isinstance(other, list):
            return self.__class__(self._entries + other)
        elif isinstance(other, Path):
            return self.__class__(self._entries + other._entries)
        raise TypeError(other)

    def __str__(self):
        """
        >>> str(Path(['foo', 0, 'bar']))
        'foo[0].bar'
        """
        path_str = ""
        for entry in self._entries:
            if isinstance(entry, int):
                path_str += "[%s]" % entry
            else:
                path_str += ".%s" % entry
        return path_str.lstrip(".")

    def __repr__(self):
        if not self._entries:
            return "<%s empty>" % (self.__class__.__name__)
        return "<%s %s>" % (self.__class__.__name__, self)

    def __eq__(self, other):
        """
        >>> Path(['foo', 0, 'bar']) == ['foo', 0, 'bar']
        True

        >>> Path(['foo', 0, 'bar']) == 'foo[0].bar'
        True

        >>> Path(['foo', 0, 'bar']) == Path(['foo', 0, 'bar'])
        True

        >>> Path() == object()
        Traceback (most recent call last):
            ...
        TypeError
        """
        if isinstance(other, list):
            return self._entries == other
        if isinstance(other, six.string_types):
            return str(self) == other
        elif isinstance(other, Path):
            return self._entries == other._entries
        raise TypeError(other)

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
