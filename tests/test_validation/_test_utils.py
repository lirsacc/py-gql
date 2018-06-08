# -*- coding: utf-8 -*-
""" """
from __future__ import print_function

from py_gql.lang import parse
from py_gql.validation import validate_ast


def _ensure_list(value):
    if isinstance(value, list):
        return value
    else:
        return [value]


def assert_validation_result(
    schema, source, expected_msgs=None, expected_locs=None, checkers=None
):
    # Prints ar ehere so we can more easily debug when running pytest with -v
    expected_msgs = expected_msgs or []
    expected_locs = expected_locs or []

    print(source)
    result = validate_ast(schema, parse(source), checkers)
    errors = result.errors

    msgs = [msg for msg, _ in errors]
    locs = [[node.loc for node in nodes] for _, nodes in errors]

    print(" [msgs] ", msgs)
    print(" [locs] ", locs)

    assert msgs == expected_msgs
    if expected_locs:
        assert locs == [_ensure_list(l) for l in expected_locs]


def assert_checker_validation_result(
    checker, schema, source, expected_msgs=None, expected_locs=None
):
    assert_validation_result(
        schema,
        source,
        expected_msgs=expected_msgs,
        expected_locs=expected_locs,
        checkers=[checker],
    )
