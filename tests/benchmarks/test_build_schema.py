# -*- coding: utf-8 -*-

from py_gql import build_schema


def test_build_github_schema(benchmark, fixture_file):
    sdl = fixture_file("github-schema.graphql")
    benchmark(build_schema, sdl)
