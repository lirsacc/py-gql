# -*- coding: utf-8 -*-
""" Getting started example epxosing a simple counter as a GraphQL API. """

from py_gql import graphql
from py_gql.schema.build import make_executable_schema

ROOT = {"counter": 0}


# 1. Define an executable schema that defines your API


def inc(root, amount):
    root["counter"] += amount
    return root["counter"]


def dec(root, amount):
    root["counter"] -= amount
    return root["counter"]


schema = make_executable_schema(
    """
    type Query {
        counter: Int
    }

    type Mutation {
        increment(amount: Int = 1): Int
        decrement(amount: Int = 1): Int
    }
    """,
    resolvers={
        "Mutation": {
            "increment": lambda root, args, c, i: inc(root, args["amount"]),
            "decrement": lambda root, args, c, i: dec(root, args["amount"]),
        }
    },
)

# 2. Execute queries against the schema

assert graphql(schema, "{ counter }", initial_value=ROOT).response() == {
    "data": {"counter": 0}
}

assert graphql(schema, "{ counte }", initial_value=ROOT).response() == {
    "errors": [
        {
            "message": (
                'Cannot query field "counte" on type "Query", '
                'did you mean "counter"?'
            ),
            "locations": [{"line": 1, "column": 3}],
        }
    ]
}

assert graphql(
    schema, "mutation { counter: increment }", initial_value=ROOT
).response() == {"data": {"counter": 1}}

assert graphql(schema, "{ counter }", initial_value=ROOT).response() == {
    "data": {"counter": 1}
}

assert graphql(
    schema, "mutation { counter: decrement(amount: 2) }", initial_value=ROOT
).response() == {"data": {"counter": -1}}

assert (
    graphql(
        schema,
        """
        mutation ($value: Int!) {
            counter: increment(amount: $value)
        }
        """,
        initial_value=ROOT,
        variables={"value": 5},
    ).response()
    == {"data": {"counter": 4}}
)
