# -*- coding: utf-8 -*-
"""
Iterable interface for the GraphQL Language lexer.
"""

# [TODO] Review the various `Lexer.read_*` methods as the use of `peek` and
# `advance` is fairly inconsistent from tweaking the code around to make the
# tests pass. They could certainly be streamlined / optimised.

# [TODO] Settle on using HEX codes or chars, this make the code a bit
# inconsistent.


from typing import Iterator, List, Optional, Union, cast

from .._string_utils import ensure_unicode, parse_block_string
from ..exc import (
    GraphQLSyntaxError,
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

EOL_CHARS = frozenset([0x000A, 0x000D])  # "\n"  # "\r"

IGNORED_CHARS = (
    frozenset([0xFEFF, 0x0009, 0x0020, 0x002C])
    | EOL_CHARS  # BOM  # \t  # SPACE  # ,
)

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
    0x0022: '"',
    0x005C: "\\",
    0x002F: "/",
    0x0062: "\u0008",
    0x0066: "\u000c",
    0x006E: "\n",
    0x0072: "\r",
    0x0074: "\t",
}


def _unexpected(
    expected: str, char: str, position: int, source: str
) -> GraphQLSyntaxError:
    if char is None:
        return UnexpectedEOF(position - 1, source)
    else:
        return UnexpectedCharacter(
            'Expected "%s" but found "%s"' % (expected, char), position, source
        )


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

    def _peek(self) -> Optional[str]:
        try:
            return self._source[self._position]
        except IndexError:
            return None

    def _read_over_whitespace(self):
        """
        Advance lexer over all ignored characters.
        """
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

    def _read_ellipsis(self) -> Ellip:
        """
        Advance lexer over an ellipsis token (...).
        """
        start = self._position
        for _ in range(3):
            char = self._peek()
            self._position += 1
            if char != ".":
                raise _unexpected(
                    ".", cast(str, char), self._position, self._source
                )
        return Ellip(start, self._position)

    def _read_string(self) -> String:
        """
        Advance lexer over a quoted string.
        """
        start = self._position
        self._position += 1
        acc = []  # type: List[str]
        while True:
            char = self._peek()

            if char is None:
                raise NonTerminatedString("", self._position, self._source)

            code = ord(char)
            self._position += 1

            if char == '"':
                value = "".join(acc)
                return String(start, self._position, value)
            elif char == "\\":
                acc.append(self._read_escape_sequence())
            elif code == 0x000A or code == 0x000D:  # \n or \r
                raise NonTerminatedString("", self._position - 1, self._source)
            elif not (code >= 0x0020 or code == 0x0009):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

    def _read_block_string(self) -> BlockString:
        """
        Advance lexer over a triple quoted block string.
        """
        start = self._position
        self._position += 3
        acc = []  # type: List[str]

        while True:
            char = self._peek()

            if char is None:
                raise NonTerminatedString("", self._position, self._source)

            code = ord(char)

            if self._source[self._position : self._position + 3] == '"""':
                self._position += 3
                value = parse_block_string("".join(acc))
                return BlockString(start, self._position, value)

            self._position += 1

            if char == "\\":
                if self._source[self._position : self._position + 3] == '"""':
                    for _ in range(3):
                        acc.append(cast(str, self._peek()))
                        self._position += 1
                else:
                    acc.append(char)
            elif not (code >= 0x0020 or code == 0x0009 or code in EOL_CHARS):
                raise InvalidCharacter(char, self._position - 1, self._source)
            else:
                acc.append(char)

    def _read_escape_sequence(self) -> str:
        """
        Advance lexer over an escape character.

        Returns: Escaped character value
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
                "\\%s" % char, self._position - 1, self._source
            )

    def _read_escaped_unicode(self) -> str:
        """
        Advance lexer over a unicode character.

        Returns: Escaped character value
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
                "\\u%s" % escape, start - 1, self._source
            )

        try:
            return str(chr(int(escape, 16)))
        except ValueError:
            raise InvalidEscapeSequence(
                "\\u%s" % escape, start - 1, self._source
            )

    def _read_number(self) -> Union[Integer, Float]:
        """
        Advance lexer over a number.
        """
        start = self._position
        is_float = False

        char = self._peek()
        if char is not None and ord(char) == 0x002D:  # "-"
            self._position += 1

        self._read_over_integer()

        char = self._peek()

        if char is not None and ord(char) == 0x002E:  # "."
            self._position += 1
            is_float = True
            self._read_over_digits()

        char = self._peek()

        if char is not None and ord(char) in (0x0065, 0x0045):  # "e", "E"
            self._position += 1
            is_float = True
            char = self._peek()
            if char is not None and ord(char) in (0x002D, 0x002B):  # "-", "+"
                self._position += 1

            self._read_over_integer()

        end = self._position
        value = self._source[start:end]
        return (
            Float(start, end, value) if is_float else Integer(start, end, value)
        )

    def _read_over_integer(self):
        """
        Advance lexer over an integer.
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
        """
        Advance lexer over a sequence of digits.
        """
        char = self._peek()
        if char is None:
            raise UnexpectedEOF(self._position, self._source)

        code = ord(char)
        if not (0x0030 <= code <= 0x0039):
            raise UnexpectedCharacter(
                'Unexpected character "%s"' % char, self._position, self._source
            )

        while True:
            if char is not None and 0x0030 <= ord(char) <= 0x0039:
                self._position += 1
                char = self._peek()
            else:
                break

    def _read_name(self) -> Name:
        """
        Advance lexer over a name ``/[_A-Za-z][A-Za-z0-9_]+/``.
        """
        start = self._position
        while True:
            char = self._peek()
            if char is None:
                break

            code = ord(char)
            if (
                code == 0x005F
                or 0x0041 <= code <= 0x005A
                or 0x0061 <= code <= 0x007A
                or 0x0030 <= code <= 0x0039
            ):
                self._position += 1
            else:
                break

        value = self._source[start : self._position]
        return Name(start, self._position, value)

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
        char = self._peek()

        if char is None:
            self._done = True
            return EOF(self._position, self._position)

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
        elif self._source[self._position : self._position + 3] == '"""':
            return self._read_block_string()
        elif char == '"':
            return self._read_string()
        elif code == 0x002D or 0x0030 <= code <= 0x0039:
            return self._read_number()
        elif (
            code == 0x005F
            or 0x0041 <= code <= 0x005A
            or 0x0061 <= code <= 0x007A
        ):
            return self._read_name()
        else:
            raise UnexpectedCharacter(
                'Unexpected character "%s"' % char, self._position, self._source
            )
