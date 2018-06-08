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
from ..exc import (
    InvalidCharacter,
    InvalidEscapeSequence,
    NonTerminatedString,
    UnexpectedCharacter,
    UnexpectedEOF,
)
from .source import Source
from .utils import parse_block_string

EOL_CHARS = frozenset([0x000A, 0x000D])  # "\n"  # "\r"

IGNORED_CHARS = (
    frozenset([0xFEFF, 0x0009, 0x0020, 0x002C]) | EOL_CHARS  # BOM  # \t  # SPACE  # ,
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
    :rtype: bool
    """
    return code >= 0x0020 or code == 0x0009


def is_number_lead(code):
    """
    :type code: int
    :rtype: bool
    """
    return code == 0x002d or is_digit(code)


def is_digit(code):
    """
    :type code: int
    :rtype: bool
    """
    return 0x0030 <= code <= 0x0039


def is_name_lead(code):
    """
    :type code: int
    :rtype: bool
    """
    return code == 0x005f or 0x0041 <= code <= 0x005a or 0x0061 <= code <= 0x007a


def is_name_character(code):
    """
    :type code: int
    :rtype: bool
    """
    return is_name_lead(code) or is_digit(code)


class Lexer(object):
    """ GraphQL Language lexer w/ an iterator interface.

    Raises variations of ``py_gql.exc.GQLSyntaxError`` when the source is
    invalid.
    """

    __slots__ = ("source", "len", "done", "position", "started")

    def __init__(self, source):

        if source is None:
            raise ValueError("source cannot be None")

        if isinstance(source, (six.text_type, six.binary_type)):
            source = Source(source)

        self.source = source
        self.len = len(source)
        self.done = False
        self.started = False
        self.position = 0

    def peek(self, count=1, raise_on_eof=False):
        """
        :type count: int
        :type raise_on_eof: bool
        :rtype: char|None
        """
        if self.done or self.position + count - 1 >= self.len:
            if raise_on_eof:
                raise UnexpectedEOF("", self.position, self.source)
            return None
        return self.source.body[self.position + count - 1]

    def advance(self, expected=None):
        """
        :type expected: char|None
        :rtype: char|None
        """
        char = self.peek(raise_on_eof=expected is not None)
        self.position += 1

        if expected is not None and char != expected:
            raise UnexpectedCharacter(
                'Expected "%s" but found "%s"' % (expected, char),
                self.position,
                self.source,
            )

        return char

    def read_over_current_line(self):
        """ Advance lexer until the end of the current line. """
        while True:
            char = self.peek()
            if char is None:
                break
            code = ord(char)

            if is_source_character(code) and code not in EOL_CHARS:
                self.advance()
            else:
                break

    def read_over_whitespace(self):
        """ Advance lexer over all whitespace / comments / ignored chars. """
        while True:
            char = self.peek()
            if char is None:
                break
            code = ord(char)

            if code in IGNORED_CHARS:
                self.advance()
            elif code == 0x0023:  # '#'
                self.advance()
                self.read_over_current_line()
            else:
                break

    def read_ellipsis(self):
        """ Advance lexer over an ellipsis token (...).
        :rtype: py_gql.lang.token.Ellipsis
        """
        start = self.position
        for _ in range(3):
            self.advance(expected=".")
        return token.Ellipsis(start, self.position)

    def read_string(self):
        """ Advance lexer over a quoted string.
        :rtype: py_gql.lang.token.String
        """
        start = self.position
        self.advance(expected='"')
        acc = []
        while True:
            char = self.peek()

            if char is None:
                raise NonTerminatedString("", self.position, self.source)

            code = ord(char)
            self.advance()

            if char == '"':
                value = "".join(acc)
                return token.String(start, self.position, value)
            elif char == "\\":
                acc.append(self.read_escape_sequence())
            elif code == 0x000a or code == 0x000d:  # \n or \r
                raise NonTerminatedString("", self.position - 1, self.source)
            elif not is_source_character(code):
                raise InvalidCharacter(char, self.position - 1, self.source)
            else:
                acc.append(char)

        raise NonTerminatedString("", self.position, self.source)

    def read_block_string(self):
        """ Advance lexer over a quoted block string.
        :rtype: py_gql.lang.token.BlockString
        """
        start = self.position
        self.advance(expected='"')
        self.advance(expected='"')
        self.advance(expected='"')
        acc = []

        while True:
            char = self.peek()

            if char is None:
                raise NonTerminatedString("", self.position, self.source)

            code = ord(char)
            self.advance()

            if char == '"' and (self.peek(), self.peek(2)) == ('"', '"'):
                self.advance()
                self.advance()
                value = parse_block_string("".join(acc))
                return token.BlockString(start, self.position, value)
            elif char == "\\":
                if (self.peek(), self.peek(2), self.peek(3)) == ('"', '"', '"'):
                    for _ in range(3):
                        acc.append(self.advance())
                else:
                    acc.append(char)
            elif not (is_source_character(code) or code in EOL_CHARS):
                raise InvalidCharacter(char, self.position - 1, self.source)
            else:
                acc.append(char)

        raise NonTerminatedString("", self.position, self.source)

    def read_escape_sequence(self):
        """ Advance lexer over an escape character
        :rtype: char
        """
        char = self.advance()
        if char is None:
            raise NonTerminatedString("", self.position, self.source)

        code = ord(char)

        if code in QUOTED_CHARS:
            return QUOTED_CHARS[code]
        elif code == 0x0075:  # unicode character: uXXXX
            return self.read_escaped_unicode()
        else:
            raise InvalidEscapeSequence(u"\%s" % char, self.position - 1, self.source)

    def read_escaped_unicode(self):
        """ Advance lexer over a unicode character
        :rtype: char
        """
        start = self.position
        for _ in range(4):
            char = self.advance()
            if char is None:
                raise NonTerminatedString("", self.position, self.source)
            if not char.isalnum():
                break

        escape = self.source.body[start : self.position]

        if len(escape) != 4:
            raise InvalidEscapeSequence(u"\\u%s" % escape, start - 1, self.source)

        try:
            return u"%c" % six.unichr(int(escape, 16))
        except ValueError:
            raise InvalidEscapeSequence(u"\\u%s" % escape, start - 1, self.source)

    def read_number(self):
        """ Advance lexer over a number
        :rtype: py_gql.lang.token.Integer|py_gql.lang.token.Float
        """
        start = self.position
        is_float = False

        char = self.peek(raise_on_eof=True)
        if ord(char) == 0x002d:  # "-"
            self.advance()

        self.read_over_integer()

        char = self.peek()
        if char is not None and ord(char) == 0x002e:  # "."
            self.advance()
            is_float = True
            self.read_over_digits()

        char = self.peek()
        if char is not None and ord(char) in (0x0065, 0x0045):  # "e", "E"
            self.advance()
            is_float = True
            char = self.peek(raise_on_eof=True)
            if ord(char) in (0x002d, 0x002b):  # "-", "+"
                self.advance()

            self.read_over_integer()

        end = self.position
        value = self.source.body[start:end]
        return (
            token.Float(start, end, value)
            if is_float
            else token.Integer(start, end, value)
        )

    def read_over_integer(self):
        """
        :rtype: int
        """
        char = self.peek(raise_on_eof=True)
        code = ord(char)

        if code == 0x0030:  # "0"
            self.advance()
            char = self.peek()
            if char is not None and ord(char) == 0x0030:
                raise UnexpectedCharacter("%s" % char, self.position, self.source)
        else:
            self.read_over_digits()

    def read_over_digits(self):
        """
        """
        char = self.peek(raise_on_eof=True)
        code = ord(char)
        if not is_digit(code):
            raise UnexpectedCharacter("%s" % char, self.position, self.source)

        while True:
            char = self.peek()
            if char is not None and is_digit(ord(char)):
                self.advance()
            else:
                break

    def read_name(self):
        """ Advance lexer over a name /[_A-Za-z][A-Za-z0-9_]+/.
        :rtype: py_gql.lang.token.Name
        """
        start = self.position
        char = self.peek(raise_on_eof=True)
        while True:
            char = self.peek()
            if char is not None and is_name_character(ord(char)):
                self.advance()
            else:
                break

        end = self.position
        value = self.source.body[start:end]
        return token.Name(start, end, value)

    def __iter__(self):
        return self

    def __next__(self):
        """ Iterator interface.
        :rtype: py_gql.lang.token.Token
        """
        if self.done:
            raise StopIteration()

        if not self.started:
            self.started = True
            return token.SOF(0, 0)

        self.read_over_whitespace()
        char = self.peek()

        if char is None:
            self.done = True
            return token.EOF(self.position, self.position)

        code = ord(char)
        if not is_source_character(code):
            self.advance()
            raise InvalidCharacter(char, self.position, self.source)

        if char in SYMBOLS:
            start = self.position
            self.advance()
            return SYMBOLS[char](start, self.position)
        elif char == ".":
            return self.read_ellipsis()
        elif char == '"':
            if (self.peek(2), self.peek(3)) == ('"', '"'):
                return self.read_block_string()
            return self.read_string()
        elif is_number_lead(code):
            return self.read_number()
        elif is_name_lead(code):
            return self.read_name()
        else:
            raise UnexpectedCharacter(char, self.position, self.source)

    next = __next__  # Python 2 iteraator interface
