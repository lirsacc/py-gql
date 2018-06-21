# -*- coding: utf-8 -*-
""" Iterable interface for the GraphQL Language lexer.

The ``py_gql.lang.lexer.Lexer`` provides an iterable interface over
tokenizing the Grahpql source.
- All valid tokens returned by the lexer can be found in ``py_gql.lang.token``.
- All exceptions relevant to tokenizking are subclasses of
  ``py_gql.exc.GQLSyntaxError``.
"""

# [TODO] Review the various `Lexer.read_*` methods as the use of `peek` and
# `advance` is fairly inconsistent from tweaking the code around to make the
# tests pass. They could certainly be streamlined / optimised.

# [TODO] Settle on using HEX codes or chars, this make the code a bit
# inconsistent.

import six

from . import token
from .._string_utils import ensure_unicode, parse_block_string
from ..exc import (
    InvalidCharacter,
    InvalidEscapeSequence,
    NonTerminatedString,
    UnexpectedCharacter,
    UnexpectedEOF,
)

EOL_CHARS = frozenset([0x000A, 0x000D])  # "\n"  # "\r"

IGNORED_CHARS = (
    frozenset([0xFEFF, 0x0009, 0x0020, 0x002C])
    | EOL_CHARS  # BOM  # \t  # SPACE  # ,
)

SYMBOLS = {
    cls.__char__: cls
    for cls in (
        token.ExclamationMark,
        token.Dollar,
        token.ParenOpen,
        token.ParenClose,
        token.BracketOpen,
        token.BracketClose,
        token.CurlyOpen,
        token.CurlyClose,
        token.Colon,
        token.Equals,
        token.At,
        token.Pipe,
        token.Ampersand,
    )
}

QUOTED_CHARS = {
    0x0022: u'"',
    0x005c: u"\\",
    0x002f: u"/",
    0x0062: u"\u0008",
    0x0066: u"\u000c",
    0x006e: u"\n",
    0x0072: u"\r",
    0x0074: u"\t",
}


def is_source_character(code):
    """
    :type code: int
    :param code:

    :rtype: bool
    """
    return code >= 0x0020 or code == 0x0009


def is_number_lead(code):
    """
    :type code: int
    :param code:

    :rtype: bool
    """
    return code == 0x002d or is_digit(code)


def is_digit(code):
    """
    :type code: int
    :param code:

    :rtype: bool
    """
    return 0x0030 <= code <= 0x0039


def is_name_lead(code):
    """
    :type code: int
    :param code:

    :rtype: bool
    """
    return (
        code == 0x005f or 0x0041 <= code <= 0x005a or 0x0061 <= code <= 0x007a
    )


def is_name_character(code):
    """
    :type code: int
    :param code:

    :rtype: bool
    """
    return is_name_lead(code) or is_digit(code)


class Lexer(object):
    """ Iterable GraphQL language lexer.

    This class is not typically exposed through the parser but can be used
    independently.

    Each call to ``__next__`` will read over a number of characters required
    to form a valid :class:`py_gql.lang.token.Token` and otherwise raise
    :class:`py_gql.exc.GraphQLSyntaxError` if that is not possible.
    """

    __slots__ = "_source", "_len", "_done", "_position", "_started"

    def __init__(self, source):

        if source is None:
            raise ValueError("source cannot be None")

        self._source = ensure_unicode(source)
        self._len = len(source)
        self._done = False
        self._started = False
        self._position = 0

    def _peek(self, count=1, raise_on_eof=False):
        """
        :type count: int
        :param count:

        :type raise_on_eof: bool
        :param raise_on_eof:

        :rtype: Optional[char]
        """
        if self._done or self._position + count - 1 >= self._len:
            if raise_on_eof:
                raise UnexpectedEOF(self._position, self._source)
            return None
        return self._source[self._position + count - 1]

    def _advance(self, expected=None):
        """
        :type expected: Optional[char]
        :param expected:

        :rtype: Optional[char]
        """
        char = self._peek(raise_on_eof=expected is not None)
        self._position += 1

        if expected is not None and char != expected:
            raise UnexpectedCharacter(
                'Expected "%s" but found "%s"' % (expected, char),
                self._position,
                self._source,
            )

        return char

    def _read_over_current_line(self):
        """ Advance lexer until the end of the current line. """
        while True:
            char = self._peek()
            if char is None:
                break
            code = ord(char)

            if is_source_character(code) and code not in EOL_CHARS:
                self._advance()
            else:
                break

    def _read_over_whitespace(self):
        """ Advance lexer over all whitespace / comments / ignored characters. """
        while True:
            char = self._peek()
            if char is None:
                break
            code = ord(char)

            if code in IGNORED_CHARS:
                self._advance()
            elif code == 0x0023:  # '#'
                self._advance()
                self._read_over_current_line()
            else:
                break

    def _read_ellipsis(self):
        """ Advance lexer over an ellipsis token (...).

        :rtype: py_gql.lang.token.Ellipsis
        """
        start = self._position
        for _ in range(3):
            self._advance(expected=".")
        return token.Ellipsis(start, self._position)

    def _read_string(self):
        """ Advance lexer over a quoted string.

        :rtype: py_gql.lang.token.String
        """
        start = self._position
        self._advance(expected='"')
        acc = []
        while True:
            char = self._peek()

            if char is None:
                raise NonTerminatedString("", self._position, self._source)

            code = ord(char)
            self._advance()

            if char == '"':
                value = "".join(acc)
                return token.String(start, self._position, value)
            elif char == "\\":
                acc.append(self._read_escape_sequence())
            elif code == 0x000a or code == 0x000d:  # \n or \r
                raise NonTerminatedString("", self._position - 1, self._source)
            elif not is_source_character(code):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

        raise NonTerminatedString("", self._position, self._source)

    def _read_block_string(self):
        """ Advance lexer over a triple quoted block string.

        :rtype: py_gql.lang.token.BlockString
        """
        start = self._position
        self._advance(expected='"')
        self._advance(expected='"')
        self._advance(expected='"')
        acc = []

        while True:
            char = self._peek()

            if char is None:
                raise NonTerminatedString("", self._position, self._source)

            code = ord(char)
            self._advance()

            if char == '"' and (self._peek(), self._peek(2)) == ('"', '"'):
                self._advance()
                self._advance()
                value = parse_block_string("".join(acc))
                return token.BlockString(start, self._position, value)
            elif char == "\\":
                if (self._peek(), self._peek(2), self._peek(3)) == (
                    '"',
                    '"',
                    '"',
                ):
                    for _ in range(3):
                        acc.append(self._advance())
                else:
                    acc.append(char)
            elif not (is_source_character(code) or code in EOL_CHARS):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

        raise NonTerminatedString("", self._position, self._source)

    def _read_escape_sequence(self):
        """ Advance lexer over an escape character

        :rtype: char
        """
        char = self._advance()
        if char is None:
            raise NonTerminatedString("", self._position, self._source)

        code = ord(char)

        if code in QUOTED_CHARS:
            return QUOTED_CHARS[code]
        elif code == 0x0075:  # unicode character: uXXXX
            return self._read_escaped_unicode()
        else:
            raise InvalidEscapeSequence(
                u"\%s" % char, self._position - 1, self._source
            )

    def _read_escaped_unicode(self):
        """ Advance lexer over a unicode character

        :rtype: char
        """
        start = self._position
        for _ in range(4):
            char = self._advance()
            if char is None:
                raise NonTerminatedString("", self._position, self._source)
            if not char.isalnum():
                break

        escape = self._source[start : self._position]

        if len(escape) != 4:
            raise InvalidEscapeSequence(
                u"\\u%s" % escape, start - 1, self._source
            )

        try:
            return u"%c" % six.unichr(int(escape, 16))
        except ValueError:
            raise InvalidEscapeSequence(
                u"\\u%s" % escape, start - 1, self._source
            )

    def _read_number(self):
        """ Advance lexer over a number

        :rtype: Union[py_gql.lang.token.Integer, py_gql.lang.token.Float]
        """
        start = self._position
        is_float = False

        char = self._peek(raise_on_eof=True)
        if ord(char) == 0x002d:  # "-"
            self._advance()

        self._read_over_integer()

        char = self._peek()
        if char is not None and ord(char) == 0x002e:  # "."
            self._advance()
            is_float = True
            self._read_over_digits()

        char = self._peek()
        if char is not None and ord(char) in (0x0065, 0x0045):  # "e", "E"
            self._advance()
            is_float = True
            char = self._peek(raise_on_eof=True)
            if ord(char) in (0x002d, 0x002b):  # "-", "+"
                self._advance()

            self._read_over_integer()

        end = self._position
        value = self._source[start:end]
        return (
            token.Float(start, end, value)
            if is_float
            else token.Integer(start, end, value)
        )

    def _read_over_integer(self):
        """ Advance lexer over an integer

        :rtype: int
        """
        char = self._peek(raise_on_eof=True)
        code = ord(char)

        if code == 0x0030:  # "0"
            self._advance()
            char = self._peek()
            if char is not None and ord(char) == 0x0030:
                raise UnexpectedCharacter(
                    "%s" % char, self._position, self._source
                )
        else:
            self._read_over_digits()

    def _read_over_digits(self):
        """ Advance lexer over a sequence of digits """
        char = self._peek(raise_on_eof=True)
        code = ord(char)
        if not is_digit(code):
            raise UnexpectedCharacter("%s" % char, self._position, self._source)

        while True:
            char = self._peek()
            if char is not None and is_digit(ord(char)):
                self._advance()
            else:
                break

    def _read_name(self):
        """ Advance lexer over a name ``/[_A-Za-z][A-Za-z0-9_]+/``.

        :rtype: py_gql.lang.token.Name
        """
        start = self._position
        char = self._peek(raise_on_eof=True)
        while True:
            char = self._peek()
            if char is not None and is_name_character(ord(char)):
                self._advance()
            else:
                break

        end = self._position
        value = self._source[start:end]
        return token.Name(start, end, value)

    def __iter__(self):
        return self

    def __next__(self):
        """

        :rtype: py_gql.lang.token.Token

        :Raises:

            - :class:`py_gql.exc.UnexpectedEOF`
            - :class:`py_gql.exc.InvalidCharacter`
            - :class:`py_gql.exc.UnexpectedCharacter`
            - :class:`py_gql.exc.NonTerminatedString`
        """
        if self._done:
            raise StopIteration()

        if not self._started:
            self._started = True
            return token.SOF(0, 0)

        self._read_over_whitespace()
        char = self._peek()

        if char is None:
            self._done = True
            return token.EOF(self._position, self._position)

        code = ord(char)
        if not is_source_character(code):
            self._advance()
            raise InvalidCharacter(char, self._position, self._source)

        if char in SYMBOLS:
            start = self._position
            self._advance()
            return SYMBOLS[char](start, self._position)
        elif char == ".":
            return self._read_ellipsis()
        elif char == '"':
            if (self._peek(2), self._peek(3)) == ('"', '"'):
                return self._read_block_string()
            return self._read_string()
        elif is_number_lead(code):
            return self._read_number()
        elif is_name_lead(code):
            return self._read_name()
        else:
            raise UnexpectedCharacter(char, self._position, self._source)

    next = __next__  # Python 2 iterator interface
