# -*- coding: utf-8 -*-
""" ported from graphql-js """

from py_gql.lang.utils import parse_block_string


def test_it_removes_uniform_indentation_from_a_string():
    raw_value = "\n".join(
        ["", "    Hello,", "      World!", "", "    Yours,", "      GraphQL."]
    )
    assert parse_block_string(raw_value) == "\n".join(
        ["Hello,", "  World!", "", "Yours,", "  GraphQL."]
    )


def test_it_removes_empty_leading_and_trailing_lines():
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


def test_it_removes_blank_leading_and_trailing_lines():
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


def test_it_retains_indentation_from_first_line():
    raw_value = "\n".join(
        ["    Hello,", "      World!", "", "    Yours,", "      GraphQL."]
    )

    assert parse_block_string(raw_value) == "\n".join(
        ["    Hello,", "  World!", "", "Yours,", "  GraphQL."]
    )


def test_it_does_not_alter_trailing_spaces():
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
