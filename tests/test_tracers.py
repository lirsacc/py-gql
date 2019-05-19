# -*- coding: utf-8 -*-

import datetime

from py_gql import graphql_blocking
from py_gql.tracers import ApolloTracer


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
        instrumentation=tracer,
    )

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


def test_ApolloTracer_on_validation_error(starwars_schema):
    tracer = ApolloTracer()

    graphql_blocking(
        starwars_schema,
        """
        query NestedQuery {
            hero {
                nameasd  # this is the validation error
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
        instrumentation=tracer,
    )

    assert tracer.name == "tracing"
    assert tracer.payload() == {
        "version": 1,
        "startTime": AnyTimestamp(),
        "endTime": AnyTimestamp(),
        "duration": AnyInt(),
        "execution": None,
        "validation": {"duration": AnyInt(), "startOffset": AnyInt()},
        "parsing": {"duration": AnyInt(), "startOffset": AnyInt()},
    }


def test_ApolloTracer_on_syntax_error(starwars_schema):
    tracer = ApolloTracer()

    graphql_blocking(
        starwars_schema,
        """
        FOO
        """,
        instrumentation=tracer,
    )

    assert tracer.name == "tracing"
    assert tracer.payload() == {
        "version": 1,
        "startTime": AnyTimestamp(),
        "endTime": AnyTimestamp(),
        "duration": AnyInt(),
        "execution": None,
        "validation": None,
        "parsing": {"duration": AnyInt(), "startOffset": AnyInt()},
    }
