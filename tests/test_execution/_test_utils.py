# -*- coding: utf-8 -*-

import pytest

from py_gql.execution import execute
from py_gql.execution.executors import SyncExecutor, ThreadPoolExecutor
from py_gql.lang import parse


def _dict(value):
    if isinstance(value, list):
        return [_dict(x) for x in value]
    elif isinstance(value, dict):
        return {k: _dict(v) for k, v in value.items()}
    else:
        return value


def _simplify_errors(errors):
    return [(str(err), node.loc, str(path)) for err, node, path in errors]


def check_execution(
    schema,
    query,
    expected_data=None,
    expected_errors=None,
    expected_exc=None,
    expected_msg=None,
    **ex_kwargs
):

    doc = parse(query)

    if expected_exc is not None:
        with pytest.raises(expected_exc) as exc_info:
            execute(schema, doc, **ex_kwargs)
        if expected_msg is not None:
            assert str(exc_info.value) == expected_msg

    else:
        data, errors = execute(schema, doc, **ex_kwargs)

        import pprint

        pprint.pprint(_dict(data))
        pprint.pprint(_dict(expected_data))
        pprint.pprint(_simplify_errors(errors))

        if expected_data is not None:
            assert data == expected_data

        if expected_errors is not None:
            assert _simplify_errors(errors) == expected_errors


# Default executors under tests
TESTED_EXECUTORS = [(SyncExecutor, {}), (ThreadPoolExecutor, {"max_workers": 10})]
