# -*- coding: utf-8 -*-

import pytest

from py_gql.lang import ast as _ast


@pytest.mark.parametrize(
    "rhs,lhs,eq",
    [
        (
            _ast.Name("foo", " ... ", (0, 1)),
            _ast.Name("foo", "  ", (0, 1)),
            True,
        ),
        (
            _ast.Name("foo", " ... ", (0, 1)),
            _ast.Name("foo", "  ", (0, 2)),
            False,
        ),
        (
            _ast.Name("bar", " ... ", (0, 1)),
            _ast.Name("foo", "  ", (0, 1)),
            False,
        ),
        (
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-byte character."
                        ),
                    )
                ],
            ),
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-byte character."
                        ),
                    )
                ],
            ),
            True,
        ),
        (
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-byte character."
                        ),
                    )
                ],
            ),
            _ast.Field(
                name=_ast.Name(value="field2"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-byte character."
                        ),
                    )
                ],
            ),
            False,
        ),
        (
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-byte character."
                        ),
                    )
                ],
            ),
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-bytes character."
                        ),
                    )
                ],
            ),
            False,
        ),
    ],
)
def test_eq(rhs, lhs, eq):
    if eq:
        assert rhs == lhs
    else:
        assert rhs != lhs


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            _ast.Name("foo", " ... ", (0, 1)),
            {"__kind__": "Name", "loc": (0, 1), "value": "foo"},
        ),
        (
            _ast.Field(
                name=_ast.Name(value="field"),
                arguments=[
                    _ast.Argument(
                        name=_ast.Name(value="arg"),
                        value=_ast.StringValue(
                            value="Has a \u0A0A multi-bytes character."
                        ),
                    )
                ],
            ),
            {
                "__kind__": "Field",
                "alias": None,
                "arguments": [
                    {
                        "__kind__": "Argument",
                        "loc": None,
                        "name": {
                            "__kind__": "Name",
                            "loc": None,
                            "value": "arg",
                        },
                        "value": {
                            "__kind__": "StringValue",
                            "block": False,
                            "loc": None,
                            "value": "Has a ਊ multi-bytes character.",
                        },
                    }
                ],
                "directives": [],
                "loc": None,
                "name": {"__kind__": "Name", "loc": None, "value": "field"},
                "response_name": "field",
                "selection_set": None,
            },
        ),
    ],
)
def test_to_dict(value, expected):
    assert expected == value.to_dict()
