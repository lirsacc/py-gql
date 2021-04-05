from py_gql import build_schema
from py_gql.lang import parse
from py_gql.utilities import introspection_query
from py_gql.validation import validate_with_rules


def test_validate_introspection_query(benchmark, fixture_file):
    schema = build_schema(fixture_file("github-schema.graphql"))
    doc = parse(introspection_query())
    benchmark(validate_with_rules, schema, doc)
