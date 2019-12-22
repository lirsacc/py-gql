# -*- coding: utf-8 -*-
""" Global fixtures """

import os

import pytest

from py_gql import build_schema


@pytest.fixture
def fixture_file():
    """ Helper to load fixture files by name. """

    def load(name):
        filepath = os.path.join(os.path.dirname(__file__), "fixtures", name)
        with open(filepath, "rb") as f:
            return f.read().decode("utf-8")

    return load


@pytest.fixture
def starwars_schema():
    from ._star_wars import StarWarsSchema

    return StarWarsSchema


@pytest.fixture
def github_schema(fixture_file):
    return build_schema(fixture_file("github-schema.graphql"))


@pytest.fixture
def raiser():
    def factory(cls, *args, **kwargs):
        assert issubclass(cls, Exception)

        def _raiser(*_a, **_kw):
            raise cls(*args, **kwargs)

        return _raiser

    return factory
