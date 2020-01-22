# -*- coding: utf-8 -*-

import pprint
from concurrent.futures import Future
from inspect import isawaitable
from typing import Any, List, Optional, Tuple, Type, Union

import pytest

from py_gql import process_graphql_query
from py_gql._string_utils import dedent, stringify_path
from py_gql.execution import GraphQLResult, execute
from py_gql.lang import parse
from py_gql.lang.ast import Document
from py_gql.schema import Field, GraphQLType, ObjectType, Schema

ExpectedError = Tuple[str, Tuple[int, int], Optional[str]]
ExpectedExcDef = Union[Type[Exception], Tuple[Type[Exception], Optional[str]]]


def create_test_schema(field_or_type, **kwargs):
    if isinstance(field_or_type, GraphQLType):
        return Schema(
            ObjectType("Query", [Field("test", field_or_type, **kwargs)])
        )
    else:
        return Schema(ObjectType("Query", [field_or_type]))


def assert_execution_result(
    result: GraphQLResult,
    expected_data: Any = None,
    expected_errors: Optional[List[ExpectedError]] = None,
) -> None:
    data, errors = result

    simplified_errors = [
        (
            str(err),
            err.nodes[0].loc if err.nodes else None,
            stringify_path(err.path),
        )
        for err in (errors or [])
    ]

    # Prints out in failed tests when running with -vv
    print("Result:")
    print("-------")
    pprint.pprint(data)
    pprint.pprint(simplified_errors)

    print("Expected:")
    print("---------")
    pprint.pprint(expected_data)
    pprint.pprint(expected_errors)

    # TODO: Remove this guard
    if expected_data is not None:
        assert expected_data == data

    if expected_errors:
        assert set(expected_errors) == set(simplified_errors)
    else:
        assert not errors


def ensure_document(doc: Union[Document, str]) -> Document:
    if not isinstance(doc, Document):
        # Always dedent so results are consistent after reflowing multiline queries
        return parse(dedent(doc))
    return doc


def assert_sync_execution(
    schema: Schema,
    doc: Union[Document, str],
    expected_data: Any = None,
    expected_errors: Optional[List[ExpectedError]] = None,
    expected_exc: Optional[ExpectedExcDef] = None,
    **kwargs: Any
) -> None:
    doc = ensure_document(doc)

    if isinstance(expected_exc, tuple):
        expected_exc, expected_msg = expected_exc
    else:
        expected_exc, expected_msg = expected_exc, None

    if expected_exc is not None:
        with pytest.raises(expected_exc) as exc_info:
            execute(schema, doc, **kwargs)

        if expected_msg:
            assert str(exc_info.value) == expected_msg
    else:
        result = execute(schema, doc, **kwargs)
        assert not isawaitable(result) and isinstance(result, GraphQLResult)
        assert_execution_result(result, expected_data, expected_errors)


async def assert_execution(
    schema: Schema,
    doc: Union[Document, str],
    expected_data: Any = None,
    expected_errors: Optional[List[ExpectedError]] = None,
    expected_exc: Optional[ExpectedExcDef] = None,
    **kwargs: Any
) -> None:
    if isinstance(expected_exc, tuple):
        expected_exc, expected_msg = expected_exc
    else:
        expected_exc, expected_msg = expected_exc, None

    async def _execute():
        result = execute(schema, ensure_document(doc), **kwargs)
        if isawaitable(result):
            return await result
        elif isinstance(result, Future):
            return result.result(timeout=2)
        return result

    if expected_exc is not None:
        with pytest.raises(expected_exc) as exc_info:
            await _execute()

        if expected_msg:
            assert str(exc_info.value) == expected_msg
    else:
        result = await _execute()
        assert isinstance(result, GraphQLResult)
        assert_execution_result(result, expected_data, expected_errors)


async def process_request(
    schema: Schema, query: str, **kwargs: Any
) -> GraphQLResult:
    result = process_graphql_query(schema, query, **kwargs)
    if isawaitable(result):
        return await result  # type: ignore
    elif isinstance(result, Future):
        return result.result(timeout=2)  # type: ignore
    return result  # type: ignore
