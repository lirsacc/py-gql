# -*- coding: utf-8 -*-
"""
py_gql.lang

The :mod:`py_gql.lang` module is responsible for parsing and operating on the
GraphQL language and source files.

You can refer to the `relevant part of the spec
<https://graphql.github.io/graphql-spec/June2018/#sec-Language>`_ for more
information.
"""

# NOTE: Lexer and Parser are both custom implemetations for now. It may be
# useful to evaluate using parser generators (PEG, Lark, etc.) in order to not
# have to maintain that code. Also this could easily be converted to C / Rust
# once it works in order to expose a compiled version. I guess we could likely
# achieve less code and similar to better performance. This would also require
# as good error messages which eliminates some parser generators with bad
# disambiguation. It would also make the implementation not pure python which is
# pretty nice to have. Overall, this is unlikely to be the main bottleneck and
# given the downsides, this is definitely low prio as long as the current
# implementation is fast enough.

from .lexer import Lexer
from .parser import Parser, parse, parse_type, parse_value
from .printer import print_ast


__all__ = ("parse", "parse_type", "parse_value", "print_ast", "Parser", "Lexer")
