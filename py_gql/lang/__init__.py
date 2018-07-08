# -*- coding: utf-8 -*-
"""
The :mod:`py_gql.lang` module is responsible for parsing and operating on
the GraphQL language and source files.
"""

# flake8: noqa

# REVIEW: Lexer and Parser are both custom implemetations for now. It may be
# useful to evaluate using parser generators (PEG, etc.) in order to not have
# to maintain that code. Also this could easily be converted to C / Rust once
# it works in order to expose a C compiled version.
# I guess we could likely
# achieve less code (sure) and similar to better performance (to be proven).
# This would also require as good error messages which eliminates some parser
# generators with bad disambiguation. Anyway, this is unlikely to be the main
# bottleneck so this is definitely low prio.

from .lexer import Lexer
from .parser import Parser, parse, parse_type, parse_value
from .printer import print_ast


__all__ = ["Lexer", "Parser", "parse", "parse_type", "parse_value", "print_ast"]
