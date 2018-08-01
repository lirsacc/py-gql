# -*- coding: utf-8 -*-
""" Iterable interface for the GraphQL Language lexer. """

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


def _unexpected(expected, char, position, source):
    if char is None:
        return UnexpectedEOF(position - 1, source)
    else:
        return UnexpectedCharacter(
            'Expected "%s" but found "%s"' % (expected, char), position, source
        )


class Lexer(object):
    """ Iterable GraphQL language lexer / tokenizer.

    This class is not typically exposed through the parser but can be used
    independently to build custom parsers.

    Each call to ``__next__`` will read over a number of characters required
    to form a valid :class:`py_gql.lang.token.Token` and otherwise raise
    :class:`~py_gql.exc.GraphQLSyntaxError` if that is not possible.

    Args:
        source (Union[str, bytes]): Source string.
            Bytestrings will be converted to unicode.
    """

    __slots__ = ("_source", "_len", "_done", "_position", "_started")

    def __init__(self, source):

        if source is None:
            raise ValueError("source cannot be None")

        self._source = ensure_unicode(source)
        self._len = len(source)
        self._done = False
        self._started = False
        self._position = 0

    def _peek(self):
        try:
            return self._source[self._position]
        except IndexError:
            return None

    def _range(self, start=0, end=1):
        return self._source[self._position + start : self._position + end]

    def _read_over_whitespace(self):
        """ Advance lexer over all ignored characters. """
        pos = self._position
        while True:
            try:
                char = self._source[pos]
            except IndexError:
                break

            code = ord(char)

            if code in IGNORED_CHARS:
                pos += 1
            elif code == 0x0023:  # '#'
                pos += 1
                while True:
                    try:
                        char = self._source[pos]
                    except IndexError:
                        break

                    code = ord(char)
                    if (
                        code >= 0x0020 or code == 0x0009
                    ) and code not in EOL_CHARS:
                        pos += 1
                    else:
                        break
            else:
                break

        self._position = pos

    def _read_ellipsis(self):
        """ Advance lexer over an ellipsis token (...).

        Returns:
            py_gql.lang.token.Ellipsis_: parse token
        """
        start = self._position
        for _ in range(3):
            char = self._peek()
            self._position += 1
            if char != ".":
                raise _unexpected(".", char, self._position, self._source)
        return token.Ellipsis_(start, self._position)

    def _read_string(self):
        """ Advance lexer over a quoted string.

        Returns:
            py_gql.lang.token.String: parse token
        """
        start = self._position
        self._position += 1
        acc = []
        while True:
            char = self._peek()

            if char is None:
                raise NonTerminatedString("", self._position, self._source)

            code = ord(char)
            self._position += 1

            if char == '"':
                value = "".join(acc)
                return token.String(start, self._position, value)
            elif char == "\\":
                acc.append(self._read_escape_sequence())
            elif code == 0x000a or code == 0x000d:  # \n or \r
                raise NonTerminatedString("", self._position - 1, self._source)
            elif not (code >= 0x0020 or code == 0x0009):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

        raise NonTerminatedString("", self._position, self._source)

    def _read_block_string(self):
        """ Advance lexer over a triple quoted block string.

        Returns:
            py_gql.lang.token.BlockString: parse token
        """
        start = self._position
        self._position += 3
        acc = []

        while True:
            char = self._peek()

            if char is None:
                raise NonTerminatedString("", self._position, self._source)

            code = ord(char)

            if self._range(0, 3) == '"""':
                self._position += 3
                value = parse_block_string("".join(acc))
                return token.BlockString(start, self._position, value)

            self._position += 1

            if char == "\\":
                if self._range(0, 3) == '"""':
                    for _ in range(3):
                        acc.append(self._peek())
                        self._position += 1
                else:
                    acc.append(char)
            elif not (code >= 0x0020 or code == 0x0009 or code in EOL_CHARS):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

        raise NonTerminatedString("", self._position, self._source)

    def _read_escape_sequence(self):
        """ Advance lexer over an escape character

        Returns:
            chr: Escaped character value
        """
        char = self._peek()
        self._position += 1
        if char is None:
            raise NonTerminatedString("", self._position, self._source)

        code = ord(char)

        if code in QUOTED_CHARS:
            return QUOTED_CHARS[code]
        elif code == 0x0075:  # unicode character: uXXXX
            return self._read_escaped_unicode()
        else:
            raise InvalidEscapeSequence(
                u"\\%s" % char, self._position - 1, self._source
            )

    def _read_escaped_unicode(self):
        """ Advance lexer over a unicode character

        Returns:
            chr: Escaped character value
        """
        start = self._position
        for _ in range(4):
            char = self._peek()
            self._position += 1
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

        Returns:
            Union[py_gql.lang.token.Integer, py_gql.lang.token.Float]:
                parse token
        """
        start = self._position
        is_float = False

        char = self._peek()
        if ord(char) == 0x002d:  # "-"
            self._position += 1

        self._read_over_integer()

        char = self._peek()

        if char is not None and ord(char) == 0x002e:  # "."
            self._position += 1
            is_float = True
            self._read_over_digits()

        char = self._peek()

        if char is not None and ord(char) in (0x0065, 0x0045):  # "e", "E"
            self._position += 1
            is_float = True
            char = self._peek()
            if char is not None and ord(char) in (0x002d, 0x002b):  # "-", "+"
                self._position += 1

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

        Returns:
            int: parsed value
        """
        char = self._peek()
        if char is None:
            raise UnexpectedEOF(self._position, self._source)

        code = ord(char)

        if code == 0x0030:  # "0"
            self._position += 1
            char = self._peek()
            if char is not None and ord(char) == 0x0030:
                raise UnexpectedCharacter(
                    'Unexpected character "%s"' % char,
                    self._position,
                    self._source,
                )
        else:
            self._read_over_digits()

    def _read_over_digits(self):
        """ Advance lexer over a sequence of digits """
        char = self._peek()
        if char is None:
            raise UnexpectedEOF(self._position, self._source)

        code = ord(char)
        if not (0x0030 <= code <= 0x0039):
            raise UnexpectedCharacter(
                'Unexpected character "%s"' % char, self._position, self._source
            )

        while True:
            char = self._peek()
            if char is not None and 0x0030 <= ord(char) <= 0x0039:
                self._position += 1
            else:
                break

    def _read_name(self):
        """ Advance lexer over a name ``/[_A-Za-z][A-Za-z0-9_]+/``.

        Returns:
            py_gql.lang.token.Name: parse token
        """
        start = self._position
        char = self._peek()
        while True:
            char = self._peek()
            if char is None:
                break

            code = ord(char)
            if (
                code == 0x005f
                or 0x0041 <= code <= 0x005a
                or 0x0061 <= code <= 0x007a
                or 0x0030 <= code <= 0x0039
            ):
                self._position += 1
            else:
                break

        end = self._position
        value = self._source[start:end]
        return token.Name(start, end, value)

    def __iter__(self):
        return self

    def __next__(self):
        """ Advance lexer and return the next :class:`py_gql.lang.token.Token`
        instance.

        Returns:
            py_gql.lang.token.Token: parse token

        Raises:
            :class:`~py_gql.exc.UnexpectedEOF`
            :class:`~py_gql.exc.InvalidCharacter`
            :class:`~py_gql.exc.UnexpectedCharacter`
            :class:`~py_gql.exc.NonTerminatedString`
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

        if not (code >= 0x0020 or code == 0x0009):
            self._position += 1
            raise InvalidCharacter(char, self._position, self._source)

        if char in SYMBOLS:
            start = self._position
            self._position += 1
            return SYMBOLS[char](start, self._position)
        elif char == ".":
            return self._read_ellipsis()
        elif self._range(0, 3) == '"""':
            return self._read_block_string()
        elif char == '"':
            return self._read_string()
        elif code == 0x002d or 0x0030 <= code <= 0x0039:
            return self._read_number()
        elif (
            code == 0x005f
            or 0x0041 <= code <= 0x005a
            or 0x0061 <= code <= 0x007a
        ):
            return self._read_name()
        else:
            raise UnexpectedCharacter(
                'Unexpected character "%s"' % char, self._position, self._source
            )

    next = __next__  # Python 2 iterator interface
