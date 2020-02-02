# -*- coding: utf-8 -*-
"""
Iterable interface for the GraphQL Language lexer.
"""

from string import ascii_letters
from typing import Container, Iterator, List, Mapping, Optional, Union

from .._string_utils import ensure_unicode, parse_block_string
from ..exc import (
    InvalidCharacter,
    InvalidEscapeSequence,
    NonTerminatedString,
    UnexpectedCharacter,
    UnexpectedEOF,
)
from .token import (
    EOF,
    SOF,
    Ampersand,
    At,
    BlockString,
    BracketClose,
    BracketOpen,
    Colon,
    CurlyClose,
    CurlyOpen,
    Dollar,
    Ellip,
    Equals,
    ExclamationMark,
    Float,
    Integer,
    Name,
    ParenClose,
    ParenOpen,
    Pipe,
    String,
    Token,
)

IGNORED_CHARS = "\n\r\ufeff\t ,"

SYMBOLS = {
    cls.value: cls
    for cls in (
        ExclamationMark,
        Dollar,
        ParenOpen,
        ParenClose,
        BracketOpen,
        BracketClose,
        CurlyOpen,
        CurlyClose,
        Colon,
        Equals,
        At,
        Pipe,
        Ampersand,
    )
}

QUOTED_CHARS = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\u0008",
    "f": "\u000c",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


class Lexer:
    """
    Iterable GraphQL language lexer / tokenizer.

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

    def __init__(self, source: Union[str, bytes]):
        self._source = ensure_unicode(source)
        self._len = len(source)
        self._done = False
        self._started = False
        self._position = 0

    def _read_over_whitespace(
        self, __ignored: Container[str] = IGNORED_CHARS
    ) -> None:
        pos = self._position
        while True:
            try:
                char = self._source[pos]
            except IndexError:
                break

            if char in __ignored:
                pos += 1
            elif char == "#":
                pos += 1
                while True:
                    try:
                        char = self._source[pos]
                    except IndexError:
                        break

                    if (char >= " " or char == "\t") and char not in "\n\r":
                        pos += 1
                    else:
                        break
            else:
                break

        self._position = pos

    def _read_ellipsis(self) -> Ellip:
        start = self._position
        for _ in range(3):
            try:
                char = self._source[self._position]
            except IndexError:
                raise UnexpectedEOF(self._position, self._source)

            self._position += 1

            if char != ".":
                raise UnexpectedCharacter(
                    'Expected "." but found "%s"' % char,
                    self._position,
                    self._source,
                )
        return Ellip(start, self._position)

    def _read_string(self) -> String:
        start = self._position
        self._position += 1
        acc = []  # type: List[str]
        while True:
            try:
                char = self._source[self._position]
            except IndexError:
                raise NonTerminatedString("", self._position, self._source)

            self._position += 1

            if char == '"':
                value = "".join(acc)
                return String(start, self._position, value)
            elif char == "\\":
                acc.append(self._read_escape_sequence())
            elif char in "\n\r":
                raise NonTerminatedString("", self._position - 1, self._source)
            elif not (char >= " " or char == "\t"):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

    def _read_block_string(self) -> BlockString:
        start = self._position
        self._position += 3
        acc = []  # type: List[str]

        while True:
            try:
                char = self._source[self._position]
            except IndexError:
                raise NonTerminatedString("", self._position, self._source)

            if self._source[self._position : self._position + 3] == '"""':
                self._position += 3
                return BlockString(
                    start, self._position, parse_block_string("".join(acc))
                )

            self._position += 1

            if char == "\\":
                if self._source[self._position : self._position + 3] == '"""':
                    acc.append('"""')
                    self._position += 3
                else:
                    acc.append(char)
            elif not (char >= " " or char in "\t\n\r"):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

    def _read_escape_sequence(
        self, __quoted_chars: Mapping[str, str] = QUOTED_CHARS
    ) -> str:

        try:
            char = self._source[self._position]
        except IndexError:
            raise NonTerminatedString("", self._position + 1, self._source)

        self._position += 1

        try:
            return __quoted_chars[char]
        except KeyError:
            pass

        if char == "u":  # unicode character: uXXXX
            return self._read_escaped_unicode()
        else:
            raise InvalidEscapeSequence(
                "\\%s" % char, self._position - 1, self._source
            )

    def _read_escaped_unicode(self) -> str:
        start = self._position
        for _ in range(4):
            try:
                char = self._source[self._position]
            except IndexError:
                raise NonTerminatedString("", self._position + 1, self._source)

            self._position += 1

            if not char.isalnum():
                break

        escape = self._source[start : self._position]

        if len(escape) != 4:
            raise InvalidEscapeSequence(
                "\\u%s" % escape, start - 1, self._source
            )

        try:
            return str(chr(int(escape, 16)))
        except ValueError:
            raise InvalidEscapeSequence(
                "\\u%s" % escape, start - 1, self._source
            )

    def _read_number(self) -> Union[Integer, Float]:  # noqa: C901
        start = self._position
        is_float = False

        try:
            char = self._source[self._position]  # type: Optional[str]
        except IndexError:
            char = None

        if char == "-":
            self._position += 1

        self._read_over_integer()

        try:
            char = self._source[self._position]
        except IndexError:
            char = None

        if char == ".":
            self._position += 1
            is_float = True
            self._read_over_digits()

        try:
            char = self._source[self._position]
        except IndexError:
            char = None

        if char is not None and char in "eE":
            self._position += 1
            is_float = True

            try:
                char = self._source[self._position]
            except IndexError:
                char = None

            if char is not None and char in "+-":
                self._position += 1

            self._read_over_integer()

        # Explicit lookahead restrictions.
        try:
            next_char = self._source[self._position]
        except IndexError:
            pass
        else:
            if next_char == "_" or next_char in ascii_letters:
                raise UnexpectedCharacter(
                    'Unexpected character "%s"' % char,
                    self._position,
                    self._source,
                )

        end = self._position
        value = self._source[start:end]
        return (
            Float(start, end, value) if is_float else Integer(start, end, value)
        )

    def _read_over_integer(self):
        try:
            char = self._source[self._position]
        except IndexError:
            raise UnexpectedEOF(self._position, self._source)

        if char == "0":
            self._position += 1
            try:
                char = self._source[self._position]
            except IndexError:
                pass
            else:
                if char.isdigit():
                    raise UnexpectedCharacter(
                        'Unexpected character "%s"' % char,
                        self._position,
                        self._source,
                    )
        else:
            self._read_over_digits()

    def _read_over_digits(self):
        try:
            char = self._source[self._position]
        except IndexError:
            raise UnexpectedEOF(self._position, self._source)

        if not (char.isdigit()):
            raise UnexpectedCharacter(
                'Unexpected character "%s"' % char, self._position, self._source
            )

        while True:
            if char is not None and char.isdigit():
                self._position += 1
                try:
                    char = self._source[self._position]
                except IndexError:
                    break
            else:
                break

    def _read_name(
        self, __ascii_letters: Container[str] = ascii_letters
    ) -> Name:
        start = self._position
        while True:
            try:
                char = self._source[self._position]
            except IndexError:
                break

            if char == "_" or char in __ascii_letters or char.isdigit():
                self._position += 1
            else:
                break

        return Name(start, self._position, self._source[start : self._position])

    def __iter__(self) -> Iterator[Token]:
        return self

    def __next__(self) -> Token:
        """
        Advance lexer and return the next :class:`py_gql.lang.Token`
        instance.

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
            return SOF(0, 0)

        self._read_over_whitespace()

        try:
            char = self._source[self._position]
        except IndexError:
            self._done = True
            return EOF(self._position, self._position)

        if not (char >= " " or char == "\t"):
            self._position += 1
            raise InvalidCharacter(char, self._position, self._source)

        if char in SYMBOLS:
            start = self._position
            self._position += 1
            return SYMBOLS[char](start, self._position)
        elif char == ".":
            return self._read_ellipsis()
        elif self._source[self._position : self._position + 3] == '"""':
            return self._read_block_string()
        elif char == '"':
            return self._read_string()
        elif char == "-" or char.isdigit():
            return self._read_number()
        elif char == "_" or char in ascii_letters:
            return self._read_name()
        else:
            raise UnexpectedCharacter(
                'Unexpected character "%s"' % char, self._position, self._source
            )
