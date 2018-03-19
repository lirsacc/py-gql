# -*- coding: utf-8 -*-
""" """

import os
import pytest


@pytest.fixture
def fixture_file():
    """ Helper to load fixture files by name. """
    def load(name):
        filepath = os.path.join(os.path.dirname(__file__), '_fixtures', name)
        with open(filepath, 'rb') as f:
            return f.read().decode('utf-8')
    return load
