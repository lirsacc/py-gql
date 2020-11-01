# -*- coding: utf-8 -*-

from py_gql._string_utils import dedent
from py_gql.lang import parse
from py_gql.validation import SPECIFIED_RULES, validate_with_rules


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
    errors = validate_with_rules(
        schema,
        parse(dedent(source), allow_type_system=True),
        rules=(checkers or SPECIFIED_RULES),
    )

    msgs = [str(err) for err in errors]
    locs = [[node.loc for node in err.nodes] for err in errors]

    print(" [msgs] ", msgs)
    print(" [locs] ", locs)

    assert msgs == expected_msgs
    if expected_locs:
        assert locs == [_ensure_list(x) for x in expected_locs]


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
