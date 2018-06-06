# -*- coding: utf-8 -*-
""" Utilities to work with GraphQL documents and syntax trees.
(Parsing and validating GraphQL source files).
"""

# flake8: noqa

# REVIEW: Lexer and Parser are both custom implemetations for now. It may be
# useful to evaluate using parser generators (PEG, etc.) in order to not have
# to maintain that code. Also this could easily be converted to C / Rust once
# it works in order to expose a C compiled version.
# Anyway, this is unlikely to be the main bottleneck so this is definitely
# low prio.

from .lexer import Lexer
from .source import Source
from .parser import Parser, parse, parse_type, parse_value
from .printer import print_ast
