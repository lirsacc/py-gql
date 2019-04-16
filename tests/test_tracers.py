# -*- coding: utf-8 -*-

import datetime
from concurrent.futures import Future
from inspect import isawaitable

import pytest

from py_gql import graphql_blocking, process_graphql_query
from py_gql.tracers import ApolloTracer, TimingTracer


# Timestamps are not deterministic
class Any:
    def __eq__(self, _):
        return True


class AnyTimestamp:
    def __eq__(self, rhs):
        try:
            datetime.datetime.strptime(rhs, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return False
        else:
            return True


class AnyInt:
    def __eq__(self, rhs):
        try:
            int(rhs)
        except ValueError:
            return False
        else:
            return True


@pytest.mark.asyncio
async def test_TimingTracer(starwars_schema, executor_cls):

    tracer = TimingTracer()

    result = process_graphql_query(
        starwars_schema,
        """
        query NestedQuery {
            hero {
                name
                friends {
                    name
                    appearsIn
                    friends {
                    name
                    }
                }
            }
        }
        """,
        tracer=tracer,
        executor_cls=executor_cls,
    )

    # Handle other executors.
    if isawaitable(result):
        result = await result
    elif isinstance(result, Future):
        result = result.result(timeout=2)

    assert tracer.start is not None
    assert tracer.end is not None
    assert tracer.parse_end is not None
    assert tracer.parse_start is not None
    assert tracer.query_end is not None
    assert tracer.query_start is not None
    assert tracer.validation_end is not None
    assert tracer.validation_start is not None

    assert [
        ("hero",),
        ("hero", "friends"),
        ("hero", "friends", 0, "appearsIn"),
        ("hero", "friends", 0, "friends"),
        ("hero", "friends", 0, "friends", 0, "name"),
        ("hero", "friends", 0, "friends", 1, "name"),
        ("hero", "friends", 0, "friends", 2, "name"),
        ("hero", "friends", 0, "friends", 3, "name"),
        ("hero", "friends", 0, "name"),
        ("hero", "friends", 1, "appearsIn"),
        ("hero", "friends", 1, "friends"),
        ("hero", "friends", 1, "friends", 0, "name"),
        ("hero", "friends", 1, "friends", 1, "name"),
        ("hero", "friends", 1, "friends", 2, "name"),
        ("hero", "friends", 1, "name"),
        ("hero", "friends", 2, "appearsIn"),
        ("hero", "friends", 2, "friends"),
        ("hero", "friends", 2, "friends", 0, "name"),
        ("hero", "friends", 2, "friends", 1, "name"),
        ("hero", "friends", 2, "friends", 2, "name"),
        ("hero", "friends", 2, "friends", 3, "name"),
        ("hero", "friends", 2, "name"),
        ("hero", "name"),
    ] == list(sorted(tracer.fields.keys()))

    for field_timing in tracer.fields.values():
        assert field_timing.start is not None
        assert field_timing.end is not None


def test_ApolloTracer(starwars_schema):
    tracer = ApolloTracer()

    graphql_blocking(
        starwars_schema,
        """
        query NestedQuery {
            hero {
                name
                friends {
                    name
                    appearsIn
                    friends {
                    name
                    }
                }
            }
        }
        """,
        tracer=tracer,
    )

    print(tracer.payload())

    assert tracer.name == "tracing"
    assert tracer.payload() == {
        "version": 1,
        "startTime": AnyTimestamp(),
        "endTime": AnyTimestamp(),
        "duration": AnyInt(),
        "execution": {"resolvers": Any()},
        "validation": {"duration": AnyInt(), "startOffset": AnyInt()},
        "parsing": {"duration": AnyInt(), "startOffset": AnyInt()},
    }

    expected_resolvers = [
        {
            "path": ["hero"],
            "parentType": "Query",
            "fieldName": "hero",
            "returnType": "Character",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "name"],
            "parentType": "Droid",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends"],
            "parentType": "Droid",
            "fieldName": "friends",
            "returnType": "[Character]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "appearsIn"],
            "parentType": "Human",
            "fieldName": "appearsIn",
            "returnType": "[Episode]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "friends"],
            "parentType": "Human",
            "fieldName": "friends",
            "returnType": "[Character]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "friends", 0, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "friends", 1, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "friends", 2, "name"],
            "parentType": "Droid",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 0, "friends", 3, "name"],
            "parentType": "Droid",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 1, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 1, "appearsIn"],
            "parentType": "Human",
            "fieldName": "appearsIn",
            "returnType": "[Episode]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 1, "friends"],
            "parentType": "Human",
            "fieldName": "friends",
            "returnType": "[Character]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 1, "friends", 0, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 1, "friends", 1, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 1, "friends", 2, "name"],
            "parentType": "Droid",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "appearsIn"],
            "parentType": "Human",
            "fieldName": "appearsIn",
            "returnType": "[Episode]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "friends"],
            "parentType": "Human",
            "fieldName": "friends",
            "returnType": "[Character]",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "friends", 0, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "friends", 1, "name"],
            "parentType": "Human",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "friends", 2, "name"],
            "parentType": "Droid",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
        {
            "path": ["hero", "friends", 2, "friends", 3, "name"],
            "parentType": "Droid",
            "fieldName": "name",
            "returnType": "String",
            "startOffset": AnyInt(),
            "duration": AnyInt(),
        },
    ]

    # Order is not deterministic.
    for r in expected_resolvers:
        assert r in tracer.payload()["execution"]["resolvers"]
