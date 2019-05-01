# -*- coding: utf-8 -*-

from py_gql.lang import parse
from py_gql.utilities import introspection_query


def parse_schema(document):
    return parse(document, allow_type_system=True)


def test_parse_kitchen_sink(benchmark, fixture_file):
    doc = fixture_file("kitchen-sink.graphql")
    benchmark(parse, doc)


def test_parse_schema_kitchen_sink(benchmark, fixture_file):
    doc = fixture_file("schema-kitchen-sink.graphql")
    benchmark(parse_schema, doc)


def test_parse_github_schema(benchmark, fixture_file):
    doc = fixture_file("github-schema.graphql")
    benchmark(parse_schema, doc)


def test_parse_introspection_query(benchmark):
    doc = introspection_query()
    benchmark(parse, doc)
