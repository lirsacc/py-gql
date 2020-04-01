# -*- coding: utf-8 -*-
from py_gql import build_schema, graphql_blocking


schema = build_schema(
    """
    type Query {
        hello(value: String = "world"): String!
    }
    """
)


@schema.resolver("Query.hello")
def resolve_hello(*_, value):
    return "Hello {}!".format(value)


result = graphql_blocking(schema, '{ hello(value: "World") }')
assert result.response() == {"data": {"hello": "Hello World!"}}
