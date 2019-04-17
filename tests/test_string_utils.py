# -*- coding: utf-8 -*-

import pytest

from py_gql._string_utils import (
    highlight_location,
    levenshtein,
    parse_block_string,
    wrapped_lines,
)


def test_highlight_location_1():
    assert (
        highlight_location(
            """{
    query {
        Node (search: "foo") {
            id
            name
        }
    }
}
""",
            40,
        )
        == """(3:27):
  1:{
  2:    query {
  3:        Node (search: "foo") {
                              ^
  4:            id
  5:            name
"""
    )


def test_highlight_location_2():
    assert (
        highlight_location(
            """{
  me {
    email
    id
    date_created
    roles {
      id
    }
    }
  }
}
""",
            80,
        )
        == """(11:1):
  09:    }
  10:  }
  11:}
     ^
  12:
"""
    )


def test_parse_block_string_removes_uniform_indentation_from_a_string():
    raw_value = "\n".join(
        ["", "    Hello,", "      World!", "", "    Yours,", "      GraphQL."]
    )
    assert parse_block_string(raw_value) == "\n".join(
        ["Hello,", "  World!", "", "Yours,", "  GraphQL."]
    )


def test_parse_block_string_removes_empty_leading_and_trailing_lines():
    raw_value = "\n".join(
        [
            "",
            "",
            "    Hello,",
            "      World!",
            "",
            "    Yours,",
            "      GraphQL.",
            "",
            "",
        ]
    )

    assert parse_block_string(raw_value) == "\n".join(
        ["Hello,", "  World!", "", "Yours,", "  GraphQL."]
    )


def test_parse_block_string_leaves_empty_leading_and_trailing_lines_alone_if_set():
    raw_value = "\n".join(
        [
            "",
            "",
            "    Hello,",
            "      World!",
            "",
            "    Yours,",
            "      GraphQL.",
            "",
            "",
        ]
    )

    assert parse_block_string(raw_value, False, False) == "\n".join(
        ["", "", "Hello,", "  World!", "", "Yours,", "  GraphQL.", "", ""]
    )


def test_parse_block_string_removes_blank_leading_and_trailing_lines():
    raw_value = "\n".join(
        [
            "  ",
            "        ",
            "    Hello,",
            "      World!",
            "",
            "    Yours,",
            "      GraphQL.",
            "        ",
            "  ",
        ]
    )

    assert parse_block_string(raw_value) == "\n".join(
        ["Hello,", "  World!", "", "Yours,", "  GraphQL."]
    )


def test_parse_block_string_retains_indentation_from_first_line():
    raw_value = "\n".join(
        ["    Hello,", "      World!", "", "    Yours,", "      GraphQL."]
    )

    assert parse_block_string(raw_value) == "\n".join(
        ["    Hello,", "  World!", "", "Yours,", "  GraphQL."]
    )


def test_parse_block_string_does_not_alter_trailing_spaces():
    raw_value = "\n".join(
        [
            "               ",
            "    Hello,     ",
            "      World!   ",
            "               ",
            "    Yours,     ",
            "      GraphQL. ",
            "               ",
        ]
    )

    assert parse_block_string(raw_value) == "\n".join(
        [
            "Hello,     ",
            "  World!   ",
            "           ",
            "Yours,     ",
            "  GraphQL. ",
        ]
    )


def test_wrapped_lines():
    source_lines = [
        "This line is shorter and should not be wrapped.",
        "This line is long and should be wrapped at around this position.",
        "This line is longer and should be wrapped twice. This line is longer and "
        "should be wrapped twice.",
        "It should also wrap around underscores like this_token",
        "and it should also wrap around dashes like this-kind-of-token.",
    ]

    assert list(wrapped_lines(source_lines, 50)) == [
        "This line is shorter and should not be wrapped.",
        "This line is long and should be wrapped at around ",
        "this position.",
        "This line is longer and should be wrapped twice. ",
        "This line is longer and should be wrapped twice.",
        "It should also wrap around underscores like this_",
        "token",
        "and it should also wrap around dashes like this-",
        "kind-of-token.",
    ]


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("", "", 0),
        ("a", "", 1),
        ("", "a", 1),
        ("abc", "", 3),
        ("", "abc", 3),
        ("", "", 0),
        ("a", "a", 0),
        ("abc", "abc", 0),
        ("", "a", 1),
        ("a", "ab", 1),
        ("b", "ab", 1),
        ("ac", "abc", 1),
        ("abcdefg", "xabxcdxxefxgx", 6),
        ("a", "", 1),
        ("ab", "a", 1),
        ("ab", "b", 1),
        ("abc", "ac", 1),
        ("xabxcdxxefxgx", "abcdefg", 6),
        ("a", "b", 1),
        ("ab", "ac", 1),
        ("ac", "bc", 1),
        ("abc", "axc", 1),
        ("xabxcdxxefxgx", "1ab2cd34ef5g6", 6),
        ("example", "samples", 3),
        ("sturgeon", "urgently", 6),
        ("levenshtein", "frankenstein", 6),
        ("distance", "difference", 5),
        ("java was neat", "scala is great", 7),
    ],
)
def test_levenshtein(a, b, expected):
    assert levenshtein(a, b) == expected
