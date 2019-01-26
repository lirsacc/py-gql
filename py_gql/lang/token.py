# -*- coding: utf-8 -*-
"""
All the valid source tokens found in GraphQL documents (as described in `this
document <http://facebook.github.io/graphql/June2018/#sec-Source-Text>`_) are
encoded as instances of :class:`Token`.
"""

from typing import Any


class Token(object):
    """ Base token class.

    All token instances can be compared by simple equality.

    Attributes:
        start (int): Starting position for this token (0-indexed)
        end (int): End position for this token (0-indexed)
        value (Optional[str]): Characters making up this token

    Args:
        start (int): Starting position for this token (0-indexed)
        end (int): End position for this token (0-indexed)
        value (Optional[str]): Characters making up this token
    """

    __slots__ = "start", "end", "value"

    def __init__(self, start: int, end: int, value: str):
        self.start = start
        self.end = end
        self.value = value

    def __repr__(self) -> str:
        return "<Token.%s: value='%s' at (%d, %d)>" % (
            self.__class__.__name__,
            self,
            self.start,
            self.end,
        )

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, rhs: Any) -> bool:
        return (
            self.__class__ is rhs.__class__
            and self.value == rhs.value
            and self.start == rhs.start
            and self.end == rhs.end
        )


class ConstToken(Token):
    __const__ = ""

    def __init__(self, start: int, end: int):
        super().__init__(start, end, self.__const__)


class SOF(ConstToken):
    __const__ = "<SOF>"


class EOF(ConstToken):
    __const__ = "<EOF>"


class ExclamationMark(ConstToken):
    __const__ = "!"


class Dollar(ConstToken):
    __const__ = "$"


class ParenOpen(ConstToken):
    __const__ = "("


class ParenClose(ConstToken):
    __const__ = ")"


class BracketOpen(ConstToken):
    __const__ = "["


class BracketClose(ConstToken):
    __const__ = "]"


class CurlyOpen(ConstToken):
    __const__ = "{"


class CurlyClose(ConstToken):
    __const__ = "}"


class Colon(ConstToken):
    __const__ = ":"


class Equals(ConstToken):
    __const__ = "="


class At(ConstToken):
    __const__ = "@"


class Pipe(ConstToken):
    __const__ = "|"


class Ampersand(ConstToken):
    __const__ = "&"


class Ellip(ConstToken):
    __const__ = "..."


class Integer(Token):
    pass


class Float(Token):
    pass


class Name(Token):
    pass


class String(Token):
    pass


class BlockString(Token):
    pass


__all__ = (
    "Token",
    "SOF",
    "EOF",
    "ExclamationMark",
    "Dollar",
    "ParenOpen",
    "ParenClose",
    "BracketOpen",
    "BracketClose",
    "CurlyOpen",
    "CurlyClose",
    "Colon",
    "Equals",
    "At",
    "Pipe",
    "Ampersand",
    "Ellip",
    "Integer",
    "Float",
    "Name",
    "String",
    "BlockString",
)
