# -*- coding: utf-8 -*-

from py_gql import graphql
from py_gql.utilities.tracers import ApolloTracer


class Any(object):
    def __eq__(self, _):
        return True


def test_it_works(starwars_schema):
    tracer = ApolloTracer()

    graphql(
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

    assert tracer.name() == "tracing"
    assert tracer.payload() == {
        "version": 1,
        "startTime": Any(),
        "endTime": Any(),
        "duration": Any(),
        "execution": {
            "resolvers": [
                {
                    "path": ["hero"],
                    "parentType": "Query",
                    "fieldName": "hero",
                    "returnType": "Character",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "name"],
                    "parentType": "Droid",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends"],
                    "parentType": "Droid",
                    "fieldName": "friends",
                    "returnType": "[Character]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "appearsIn"],
                    "parentType": "Human",
                    "fieldName": "appearsIn",
                    "returnType": "[Episode]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "friends"],
                    "parentType": "Human",
                    "fieldName": "friends",
                    "returnType": "[Character]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "friends", 0, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "friends", 1, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "friends", 2, "name"],
                    "parentType": "Droid",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 0, "friends", 3, "name"],
                    "parentType": "Droid",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 1, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 1, "appearsIn"],
                    "parentType": "Human",
                    "fieldName": "appearsIn",
                    "returnType": "[Episode]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 1, "friends"],
                    "parentType": "Human",
                    "fieldName": "friends",
                    "returnType": "[Character]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 1, "friends", 0, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 1, "friends", 1, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 1, "friends", 2, "name"],
                    "parentType": "Droid",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "appearsIn"],
                    "parentType": "Human",
                    "fieldName": "appearsIn",
                    "returnType": "[Episode]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "friends"],
                    "parentType": "Human",
                    "fieldName": "friends",
                    "returnType": "[Character]",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "friends", 0, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "friends", 1, "name"],
                    "parentType": "Human",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "friends", 2, "name"],
                    "parentType": "Droid",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
                {
                    "path": ["hero", "friends", 2, "friends", 3, "name"],
                    "parentType": "Droid",
                    "fieldName": "name",
                    "returnType": "String",
                    "startOffset": Any(),
                    "duration": Any(),
                },
            ]
        },
        "validation": {"duration": Any(), "startOffset": Any()},
        "parsing": {"duration": Any(), "startOffset": Any()},
    }
