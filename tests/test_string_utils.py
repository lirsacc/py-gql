# -*- coding: utf-8 -*-
""" ported from graphql-js """

from py_gql._string_utils import parse_block_string, wrapped_lines


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
        ["Hello,     ", "  World!   ", "           ", "Yours,     ", "  GraphQL. "]
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
