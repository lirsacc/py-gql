# -*- coding: utf-8 -*-

import collections
import random

import py_gql

SIZE = 10000

FooType = collections.namedtuple("Object", ["x", "y", "z"])

LIST_OF_INTS = [x for x in range(SIZE)]
LIST_OF_FLOATS = [random.random() for x in range(SIZE)]
LIST_OF_STRINGS = [str(x) for x in range(SIZE)]
LIST_OF_BOOLS = [bool(x % 2) for x in range(SIZE)]
LIST_OF_OBJECTS = [FooType(x, x, x) for x in range(SIZE)]
LIST_OF_DICTS = [{"x": x, "y": x, "z": x} for x in range(SIZE)]

schema = py_gql.build_schema(
    """
type Foo {
    x: Int,
    y: Int,
    z: Int,
}

type Query {
    list_of_ints: [Int],
    list_of_floats: [Float],
    list_of_string_ids: [ID],
    list_of_int_ids: [ID],
    list_of_strings: [String],
    list_of_bools: [Boolean],
    list_of_objects: [Foo],
    list_of_dicts: [Foo],
}
"""
)


@schema.resolver("Query.list_of_ints")
@schema.resolver("Query.list_of_int_ids")
def _resolve_list_of_ints(*_, **__):
    return LIST_OF_INTS


@schema.resolver("Query.list_of_objects")
def _resolve_list_of_objects(*_, **__):
    return LIST_OF_OBJECTS


@schema.resolver("Query.list_of_dicts")
def _resolve_list_of_dicts(*_, **__):
    return LIST_OF_DICTS


@schema.resolver("Query.list_of_strings")
@schema.resolver("Query.list_of_string_ids")
def _resolve_list_of_strings(*_, **__):
    return LIST_OF_STRINGS


@schema.resolver("Query.list_of_bools")
def _resolve_list_of_bools(*_, **__):
    return LIST_OF_BOOLS


@schema.resolver("Query.list_of_floats")
def _resolve_list_of_floats(*_, **__):
    return LIST_OF_FLOATS


def test_list_of_ints(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_ints }")


def test_list_of_floats(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_floats }")


def test_list_of_strings(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_strings }")


def test_list_of_bools(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_bools }")


def test_list_of_int_ids(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_int_ids }")


def test_list_of_string_ids(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_string_ids }")


def test_list_of_objects_one_field(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_objects { x } }")


def test_list_of_objects_two_fields(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_objects { x y } }")


def test_list_of_dicts_one_field(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_dicts { x } }")


def test_list_of_dicts_two_fields(benchmark):
    benchmark(py_gql.graphql_blocking, schema, "{ list_of_dicts { x y } }")


def test_introspection_query(benchmark, fixture_file):
    github_schema = py_gql.build_schema(fixture_file("github-schema.graphql"))
    query = py_gql.utilities.introspection_query()
    benchmark(py_gql.graphql_blocking, github_schema, query)
