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
    return f"Hello {value}!"


result = graphql_blocking(schema, '{ hello(value: "Foo") }')
assert result.response() == {"data": {"hello": "Hello Foo!"}}
