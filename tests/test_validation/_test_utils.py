# -*- coding: utf-8 -*-

from py_gql._string_utils import dedent
from py_gql.lang import parse
from py_gql.validation import validate_ast
from py_gql.validation.validate import SPECIFIED_RULES, default_validator


def _ensure_list(value):
    if isinstance(value, list):
        return value
    else:
        return [value]


def assert_validation_result(
    schema, source, expected_msgs=None, expected_locs=None, checkers=None
):
    # Prints are here so we can more easily debug when running pytest with -v
    expected_msgs = expected_msgs or []
    expected_locs = expected_locs or []
    print(source)
    result = validate_ast(
        schema,
        parse(dedent(source), allow_type_system=True),
        validators=[
            lambda s, d, v: default_validator(
                s, d, v, validators=(checkers or SPECIFIED_RULES)
            )
        ],
    )
    errors = result.errors

    msgs = [str(err) for err in errors]
    locs = [[node.loc for node in err.nodes] for err in errors]

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
