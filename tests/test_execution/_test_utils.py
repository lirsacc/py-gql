# -*- coding: utf-8 -*-

import pprint

import pytest

from py_gql._string_utils import stringify_path
from py_gql.execution import execute
from py_gql.execution.executors import SyncExecutor, ThreadPoolExecutor
from py_gql.lang import ast as _ast, parse


def _dict(value):
    if isinstance(value, list):
        return [_dict(x) for x in value]
    elif isinstance(value, dict):
        return {k: _dict(v) for k, v in value.items()}
    else:
        return value


def _simplify_errors(errors):
    return [
        (
            str(err),
            err.nodes[0].loc if err.nodes else None,
            stringify_path(err.path),
        )
        for err in errors
    ]


def check_execution(
    schema,
    query,
    expected_data=None,
    expected_errors=None,
    expected_exc=None,
    expected_msg=None,
    **ex_kwargs
):

    if isinstance(query, _ast.Document):
        doc = query
    else:
        doc = parse(query)

    if expected_exc is not None:
        with pytest.raises(expected_exc) as exc_info:
            execute(schema, doc, **ex_kwargs).result()
        if expected_msg is not None:
            assert str(exc_info.value) == expected_msg

    else:
        data, errors = execute(schema, doc, **ex_kwargs).result()

        print("Result:")
        print("-------")
        pprint.pprint(_dict(data))
        pprint.pprint(_simplify_errors(errors))

        print("Expected:")
        print("---------")
        pprint.pprint(_dict(expected_data))
        pprint.pprint(expected_errors)

        if expected_data is not None:
            assert data == expected_data

        if expected_errors is not None:
            assert _simplify_errors(errors) == expected_errors


# Default executors under tests
TESTED_EXECUTORS = [
    (SyncExecutor, {}),
    (ThreadPoolExecutor, {"max_workers": 10}),
]
