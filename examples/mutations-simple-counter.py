# -*- coding: utf-8 -*-
"""
Simple mutations example: incrementing and decrementing a global counter.
"""

from py_gql import build_schema, graphql_blocking


ROOT = {"counter": 0}


schema = build_schema(
    """
    type Query {
        counter: Int
    }

    type Mutation {
        increment(amount: Int = 1): Int
        decrement(amount: Int = 1): Int
    }
    """,
)


@schema.resolver("Mutation.increment")
def inc(root, *, amount):
    root["counter"] += amount
    return root["counter"]


@schema.resolver("Mutation.decrement")
def dec(root, *, amount):
    root["counter"] -= amount
    return root["counter"]


# 2. Execute queries against the schema

assert graphql_blocking(schema, "{ counter }", root=ROOT).response() == {
    "data": {"counter": 0},
}

assert graphql_blocking(schema, "{ counte }", root=ROOT).response() == {
    "errors": [
        {
            "message": (
                'Cannot query field "counte" on type "Query". Did you '
                'mean "counter"?'
            ),
            "locations": [{"line": 1, "column": 3}],
        },
    ],
}

assert (
    graphql_blocking(
        schema,
        "mutation { counter: increment }",
        root=ROOT,
    ).response()
    == {"data": {"counter": 1}}
)

assert graphql_blocking(schema, "{ counter }", root=ROOT).response() == {
    "data": {"counter": 1},
}

assert (
    graphql_blocking(
        schema,
        "mutation { counter: decrement(amount: 2) }",
        root=ROOT,
    ).response()
    == {"data": {"counter": -1}}
)

assert (
    graphql_blocking(
        schema,
        """
        mutation ($value: Int!) {
            counter: increment(amount: $value)
        }
        """,
        root=ROOT,
        variables={"value": 5},
    ).response()
    == {"data": {"counter": 4}}
)
