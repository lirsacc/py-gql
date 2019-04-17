# -*- coding: utf-8 -*-

# Test naming is not very 'pythonic' as I tried to keep a close match with the
# original ones for easy reference. Others were kept while they were specific
# to the implementation and are kept as skipped.

import pytest

from py_gql.exc import (
    InvalidCharacter,
    InvalidEscapeSequence,
    NonTerminatedString,
    UnexpectedCharacter,
    UnexpectedEOF,
)
from py_gql.lang import Lexer, token


def lex_one(source):
    lexer = Lexer(source)
    assert type(next(lexer)) == token.SOF
    return next(lexer)


def test_it_disallows_uncommon_control_characters():
    with pytest.raises(InvalidCharacter) as exc_info:
        lex_one("\u0007")
    assert exc_info.value.position == 1


def test_lex_with_trailing_whitespace():
    assert [token.SOF(0, 0), token.Name(1, 4, "foo"), token.EOF(9, 9)] == list(
        Lexer(" foo     ")
    )


def test_lex_with_trailing_whitespace_2():
    assert [
        token.SOF(0, 0),
        token.Name(1, 4, "foo"),
        token.EOF(11, 11),
    ] == list(Lexer(" foo     \n#"))


def test_it_accepts_bom_header():
    assert lex_one("\uFEFF foo") == token.Name(2, 5, "foo")


def test_it_accepts_binary_type():
    assert lex_one(b"foo") == token.Name(0, 3, "foo")


def test_it_skips_whitespace_and_comments_1():
    assert (
        lex_one(
            """

    foo


    """
        )
        == token.Name(6, 9, "foo")
    )


def test_it_skips_whitespace_and_comments_2():
    assert (
        lex_one(
            """
    #comment
    foo#comment
    """
        )
        == token.Name(18, 21, "foo")
    )


def test_it_skips_whitespace_and_comments_3():
    assert lex_one(",,,foo,,,") == token.Name(3, 6, "foo")


def test_errors_respect_whitespace():
    with pytest.raises(UnexpectedCharacter) as exc_info:
        lex_one(
            """

                ?

            """
        )

    assert str(exc_info.value) == (
        'Unexpected character "?" (3:17):\n'
        "  1:\n"
        "  2:\n"
        "  3:                ?\n"
        "                    ^\n"
        "  4:\n"
        "  5:            \n"
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ('"simple"', token.String(0, 8, "simple")),
        ('" white space "', token.String(0, 15, " white space ")),
        ('"quote \\""', token.String(0, 10, 'quote "')),
        (
            '"escaped \\n\\r\\b\\t\\f"',
            token.String(0, 20, "escaped \n\r\b\t\f"),
        ),
        ('"slashes \\\\ \\/"', token.String(0, 15, "slashes \\ /")),
        (
            '"unicode \\u1234\\u5678\\u90AB\\uCDEF"',
            token.String(0, 34, "unicode \u1234\u5678\u90AB\uCDEF"),
        ),
    ],
)
def test_it_lexes_strings(value, expected):
    assert lex_one(value) == expected


@pytest.mark.parametrize(
    "value, err_cls, expected_positon",
    [
        ('"', NonTerminatedString, 1),
        ('"no end quote', NonTerminatedString, 13),
        ("'single quotes'", UnexpectedCharacter, 0),
        ('"contains unescaped \u0007 control char"', InvalidCharacter, 20),
        ('"null-byte is not \u0000 end of file"', InvalidCharacter, 18),
        ('"multi\nline"', NonTerminatedString, 6),
        ('"multi\rline"', NonTerminatedString, 6),
        ('"\\\\', NonTerminatedString, 3),
        ('"\\', NonTerminatedString, 3),
        ('"\\u', NonTerminatedString, 4),
        ('"bad \\z esc"', InvalidEscapeSequence, 6),
        ('"bad \\x esc"', InvalidEscapeSequence, 6),
        ('"bad \\u1 esc"', InvalidEscapeSequence, 6),
        ('"bad \\u0XX1 esc"', InvalidEscapeSequence, 6),
        ('"bad \\uXXXX esc"', InvalidEscapeSequence, 6),
        ('"bad \\uFXXX esc"', InvalidEscapeSequence, 6),
        ('"bad \\uXXXF esc"', InvalidEscapeSequence, 6),
    ],
)
def test_it_lex_reports_useful_string_errors(value, err_cls, expected_positon):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == expected_positon


@pytest.mark.parametrize(
    "value, expected",
    [
        ('"""simple"""', token.BlockString(0, 12, "simple")),
        ('""" white space """', token.BlockString(0, 19, " white space ")),
        (
            '"""contains " quote"""',
            token.BlockString(0, 22, 'contains " quote'),
        ),
        (
            '"""contains \\""" triplequote"""',
            token.BlockString(0, 31, 'contains """ triplequote'),
        ),
        ('"""multi\nline"""', token.BlockString(0, 16, "multi\nline")),
        (
            '"""multi\rline\r\nnormalized"""',
            token.BlockString(0, 28, "multi\nline\nnormalized"),
        ),
        (
            '"""unescaped \\n\\r\\b\\t\\f\\u1234"""',
            token.BlockString(0, 32, "unescaped \\n\\r\\b\\t\\f\\u1234"),
        ),
        (
            '"""slashes \\\\ \\/"""',
            token.BlockString(0, 19, "slashes \\\\ \\/"),
        ),
        (
            '''"""

        spans
          multiple
            lines

        """''',
            token.BlockString(0, 68, "spans\n  multiple\n    lines"),
        ),
    ],
)
def test_it_lexes_block_strings(value, expected):
    assert lex_one(value) == expected


@pytest.mark.parametrize(
    "value, err_cls, expected_positon",
    [
        ('"""', NonTerminatedString, 3),
        ('"""no end quote', NonTerminatedString, 15),
        ('"""contains unescaped \u0007 control char"""', InvalidCharacter, 22),
        ('"""null-byte is not \u0000 end of file"""', InvalidCharacter, 20),
    ],
)
def test_it_lex_reports_useful_block_string_errors(
    value, err_cls, expected_positon
):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == expected_positon


@pytest.mark.parametrize(
    "string, expected",
    [
        ("4", token.Integer(0, 1, "4")),
        ("4.123", token.Float(0, 5, "4.123")),
        ("-4", token.Integer(0, 2, "-4")),
        ("9", token.Integer(0, 1, "9")),
        ("0", token.Integer(0, 1, "0")),
        ("-4.123", token.Float(0, 6, "-4.123")),
        ("0.123", token.Float(0, 5, "0.123")),
        ("123e4", token.Float(0, 5, "123e4")),
        ("123E4", token.Float(0, 5, "123E4")),
        ("123e-4", token.Float(0, 6, "123e-4")),
        ("123e+4", token.Float(0, 6, "123e+4")),
        ("-123e4", token.Float(0, 6, "-123e4")),
        ("-123E4", token.Float(0, 6, "-123E4")),
        ("-123e-4", token.Float(0, 7, "-123e-4")),
        ("-123e+4", token.Float(0, 7, "-123e+4")),
        ("-1.123e4567", token.Float(0, 11, "-1.123e4567")),
    ],
)
def test_it_lexes_numbers(string, expected):
    assert lex_one(string) == expected


@pytest.mark.parametrize(
    "value, err_cls, expected_positon",
    [
        ("00", UnexpectedCharacter, 1),
        ("+1", UnexpectedCharacter, 0),
        ("1.", UnexpectedEOF, 2),
        ("1.e1", UnexpectedCharacter, 2),
        (".123", UnexpectedCharacter, 2),
        ("1.A", UnexpectedCharacter, 2),
        ("-A", UnexpectedCharacter, 1),
        ("1.0e", UnexpectedEOF, 4),
        ("1.0eA", UnexpectedCharacter, 4),
    ],
)
def test_it_lex_reports_useful_number_errors(value, err_cls, expected_positon):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == expected_positon


@pytest.mark.parametrize(
    "string, expected",
    [
        ("!", token.ExclamationMark(0, 1)),
        ("$", token.Dollar(0, 1)),
        ("(", token.ParenOpen(0, 1)),
        (")", token.ParenClose(0, 1)),
        ("[", token.BracketOpen(0, 1)),
        ("]", token.BracketClose(0, 1)),
        ("{", token.CurlyOpen(0, 1)),
        ("}", token.CurlyClose(0, 1)),
        (":", token.Colon(0, 1)),
        ("=", token.Equals(0, 1)),
        ("@", token.At(0, 1)),
        ("|", token.Pipe(0, 1)),
        ("&", token.Ampersand(0, 1)),
        ("...", token.Ellip(0, 3)),
    ],
)
def test_it_lexes_punctuation(string, expected):
    assert lex_one(string) == expected


@pytest.mark.parametrize(
    "value, err_cls, pos",
    [
        ("..", UnexpectedEOF, 2),
        ("?", UnexpectedCharacter, 0),
        ("\u203B", UnexpectedCharacter, 0),
        ("\u200b", UnexpectedCharacter, 0),
    ],
)
def test_it_lex_reports_useful_unknown_character_error(value, err_cls, pos):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == pos


def test_it_lexes_multiple_tokens():
    assert (
        list(
            Lexer(
                """
    query {
        Node (search: "foo") {
            id
            name
        }
    }
    """
            )
        )
        == [
            token.SOF(0, 0),
            token.Name(5, 10, "query"),
            token.CurlyOpen(11, 12),
            token.Name(21, 25, "Node"),
            token.ParenOpen(26, 27),
            token.Name(27, 33, "search"),
            token.Colon(33, 34),
            token.String(35, 40, "foo"),
            token.ParenClose(40, 41),
            token.CurlyOpen(42, 43),
            token.Name(56, 58, "id"),
            token.Name(71, 75, "name"),
            token.CurlyClose(84, 85),
            token.CurlyClose(90, 91),
            token.EOF(96, 96),
        ]
    )


def test_kitchen_sink(fixture_file):
    source = fixture_file("kitchen-sink.graphql")
    assert list(Lexer(source))
