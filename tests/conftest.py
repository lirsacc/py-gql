# -*- coding: utf-8 -*-
""" Global fixtures """

import os

import pytest


@pytest.fixture
def fixture_file():
    """ Helper to load fixture files by name. """

    def load(name):
        filepath = os.path.join(os.path.dirname(__file__), "_fixtures", name)
        with open(filepath, "rb") as f:
            return f.read().decode("utf-8")

    return load


@pytest.fixture
def starwars_schema():
    from ._star_wars import StarWarsSchema

    return StarWarsSchema


@pytest.fixture
def raiser():
    def factory(cls, *args, **kwargs):
        assert issubclass(cls, Exception)

        def _raiser(*_a, **_kw):
            raise cls(*args, **kwargs)

        return _raiser

    return factory
