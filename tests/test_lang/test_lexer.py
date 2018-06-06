# -*- coding: utf-8 -*-
""" Lexer tests.
Ported from: https://github.com/graphql/graphql-js/blob/master/src/language/__tests__/lexer-test.js  # noqa: E501
on revision 8d1ae25de444a9b544a1fdc98e138ae91b77057c.
"""
# Test naming is not very 'pythonic' as I tried to keep a close match with the
# original ones for easy reference. Others were kept while they were specific
# to the implementation and are kept as skipped.

import pytest

from py_gql.exc import (
    InvalidCharacter, UnexpectedCharacter, NonTerminatedString,
    InvalidEscapeSequence, UnexpectedEOF)
from py_gql.lang import Lexer, token


def lex_one(source):
    lexer = Lexer(source)
    assert type(next(lexer)) == token.SOF
    return next(lexer)


def test_it_disallows_uncommon_control_characters():
    with pytest.raises(InvalidCharacter) as exc_info:
        lex_one(u"\u0007")
    assert exc_info.value.position == 1


def test_it_accepts_bom_header():
    assert lex_one(u"\uFEFF foo") == token.Name(2, 5, 'foo')


def test_it_accepts_binary_type():
    assert lex_one(b"foo") == token.Name(0, 3, 'foo')


@pytest.mark.skip('Irrelevant')
def test_it_records_line_and_column():
    pass


@pytest.mark.skip('Irrelevant')
def test_it_can_be_json_stringified_or_util_inspected():
    pass


def test_it_skips_whitespace_and_comments_1():
    assert lex_one(u"""

    foo


    """) == token.Name(6, 9, 'foo')


def test_it_skips_whitespace_and_comments_2():
    assert lex_one(u"""
    #comment
    foo#comment
    """) == token.Name(18, 21, 'foo')


def test_it_skips_whitespace_and_comments_3():
    assert lex_one(u",,,foo,,,") == token.Name(3, 6, 'foo')


@pytest.mark.skip('Irrelevant (see tests/test_errors.py)')
def test_it_errors_respect_whitespace():
    pass


@pytest.mark.skip('Irrelevant (see tests/test_errors.py)')
def test_it_updates_line_numbers_in_error_for_file_context():
    pass


@pytest.mark.skip('Irrelevant (see tests/test_errors.py)')
def test_it_updates_column_numbers_in_error_for_file_context():
    pass


@pytest.mark.parametrize("value,expected", [
    (u'"simple"', token.String(0, 8, "simple")),
    (u'" white space "', token.String(0, 15, " white space ")),
    (u'"quote \\""', token.String(0, 10, "quote \"")),
    (u'"escaped \\n\\r\\b\\t\\f"', token.String(0, 20, "escaped \n\r\b\t\f")),
    (u'"slashes \\\\ \\/"', token.String(0, 15, "slashes \\ /")),
    (u'"unicode \\u1234\\u5678\\u90AB\\uCDEF"',
     token.String(0, 34, u"unicode \u1234\u5678\u90AB\uCDEF")),
])
def test_it_lexes_strings(value, expected):
    assert lex_one(value) == expected


@pytest.mark.parametrize("value, err_cls, expected_positon", [
    (u'"', NonTerminatedString, 1),
    (u'"no end quote', NonTerminatedString, 13),
    (u"'single quotes'", UnexpectedCharacter, 0),
    (u'"contains unescaped \u0007 control char"', InvalidCharacter, 20),
    (u'"null-byte is not \u0000 end of file"', InvalidCharacter, 18),
    (u'"multi\nline"', NonTerminatedString, 6),
    (u'"multi\rline"', NonTerminatedString, 6),
    (u'"bad \\z esc"', InvalidEscapeSequence, 6),
    (u'"bad \\x esc"', InvalidEscapeSequence, 6),
    (u'"bad \\u1 esc"', InvalidEscapeSequence, 6),
    (u'"bad \\u0XX1 esc"', InvalidEscapeSequence, 6),
    (u'"bad \\uXXXX esc"', InvalidEscapeSequence, 6),
    (u'"bad \\uFXXX esc"', InvalidEscapeSequence, 6),
    (u'"bad \\uXXXF esc"', InvalidEscapeSequence, 6),
])
def test_it_lex_reports_useful_string_errors(value, err_cls, expected_positon):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == expected_positon


@pytest.mark.parametrize("value, expected", [
    (u'"""simple"""',
     token.BlockString(0, 12, "simple")),
    (u'""" white space """',
     token.BlockString(0, 19, " white space ")),
    (u'"""contains " quote"""',
     token.BlockString(0, 22, "contains \" quote")),
    (u'"""contains \\""" triplequote"""',
     token.BlockString(0, 31, 'contains """ triplequote')),
    (u'"""multi\nline"""',
     token.BlockString(0, 16, 'multi\nline')),
    (u'"""multi\rline\r\nnormalized"""',
     token.BlockString(0, 28, 'multi\nline\nnormalized')),
    (u'"""unescaped \\n\\r\\b\\t\\f\\u1234"""',
     token.BlockString(0, 32, "unescaped \\n\\r\\b\\t\\f\\u1234")),
    (u'"""slashes \\\\ \\/"""',
     token.BlockString(0, 19, 'slashes \\\\ \\/')),
    (u'''"""

        spans
          multiple
            lines

        """''', token.BlockString(0, 68, 'spans\n  multiple\n    lines')),
])
def test_it_lexes_block_strings(value, expected):
    assert lex_one(value) == expected


@pytest.mark.parametrize("value, err_cls, expected_positon", [
    (u'"""', NonTerminatedString, 3),
    (u'"""no end quote', NonTerminatedString, 15),
    (u'"""contains unescaped \u0007 control char"""', InvalidCharacter, 22),
    (u'"""null-byte is not \u0000 end of file"""', InvalidCharacter, 20),
])
def test_it_lex_reports_useful_block_string_errors(
        value, err_cls, expected_positon):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == expected_positon


@pytest.mark.parametrize("string, expected", [
    (u'4', token.Integer(0, 1, '4')),
    (u'4.123', token.Float(0, 5, '4.123')),
    (u'-4', token.Integer(0, 2, '-4')),
    (u'9', token.Integer(0, 1, '9')),
    (u'0', token.Integer(0, 1, '0')),
    (u'-4.123', token.Float(0, 6, '-4.123')),
    (u'0.123', token.Float(0, 5, '0.123')),
    (u'123e4', token.Float(0, 5, '123e4')),
    (u'123E4', token.Float(0, 5, '123E4')),
    (u'123e-4', token.Float(0, 6, '123e-4')),
    (u'123e+4', token.Float(0, 6, '123e+4')),
    (u'-123e4', token.Float(0, 6, '-123e4')),
    (u'-123E4', token.Float(0, 6, '-123E4')),
    (u'-123e-4', token.Float(0, 7, '-123e-4')),
    (u'-123e+4', token.Float(0, 7, '-123e+4')),
    (u'-1.123e4567', token.Float(0, 11, '-1.123e4567')),
])
def test_it_lexes_numbers(string, expected):
    assert lex_one(string) == expected


@pytest.mark.parametrize("value, err_cls, expected_positon", [
    (u'00', UnexpectedCharacter, 1),
    (u'+1', UnexpectedCharacter, 0),
    (u'1.', UnexpectedEOF, 2),
    (u'1.e1', UnexpectedCharacter, 2),
    (u'.123', UnexpectedCharacter, 2),
    (u'1.A', UnexpectedCharacter, 2),
    (u'-A', UnexpectedCharacter, 1),
    (u'1.0e', UnexpectedEOF, 4),
    (u'1.0eA', UnexpectedCharacter, 4),
])
def test_it_lex_reports_useful_number_errors(value, err_cls, expected_positon):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == expected_positon


@pytest.mark.parametrize("string, expected", [
    (u'!', token.ExclamationMark(0, 1)),
    (u'$', token.Dollar(0, 1)),
    (u'(', token.ParenOpen(0, 1)),
    (u')', token.ParenClose(0, 1)),
    (u'[', token.BracketOpen(0, 1)),
    (u']', token.BracketClose(0, 1)),
    (u'{', token.CurlyOpen(0, 1)),
    (u'}', token.CurlyClose(0, 1)),
    (u':', token.Colon(0, 1)),
    (u'=', token.Equals(0, 1)),
    (u'@', token.At(0, 1)),
    (u'|', token.Pipe(0, 1)),
    (u'&', token.Ampersand(0, 1)),
    (u'...', token.Ellipsis(0, 3)),
])
def test_it_lexes_punctuation(string, expected):
    assert lex_one(string) == expected


@pytest.mark.parametrize("value, err_cls, pos", [
    (u'..', UnexpectedEOF, 2),
    (u'?', UnexpectedCharacter, 0),
    (u'\u203B', UnexpectedCharacter, 0),
    (u'\u200b', UnexpectedCharacter, 0),
])
def test_it_lex_reports_useful_unknown_character_error(value, err_cls, pos):
    with pytest.raises(err_cls) as exc_info:
        lex_one(value)
    assert exc_info.value.position == pos


@pytest.mark.skip('Irrelevant')
def test_it_lex_reports_useful_information_for_dashes_in_names():
    pass


@pytest.mark.skip('Irrelevant')
def test_it_produces_double_linked_list_of_tokens_including_comments():
    pass


def test_it_lexes_multiple_tokens():
    assert list(Lexer(u"""
    query {
        Node (search: "foo") {
            id
            name
        }
    }
    """)) == [
        token.SOF(0, 0),
        token.Name(5, 10, 'query'),
        token.CurlyOpen(11, 12),
        token.Name(21, 25, 'Node'),
        token.ParenOpen(26, 27),
        token.Name(27, 33, 'search'),
        token.Colon(33, 34),
        token.String(35, 40, 'foo'),
        token.ParenClose(40, 41),
        token.CurlyOpen(42, 43),
        token.Name(56, 58, 'id'),
        token.Name(71, 75, 'name'),
        token.CurlyClose(84, 85),
        token.CurlyClose(90, 91),
        token.EOF(96, 96),
    ]


def test_kitchen_sink(fixture_file):
    source = fixture_file('kitchen-sink.graphql')
    assert list(Lexer(source))