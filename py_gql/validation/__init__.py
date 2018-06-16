# -*- coding: utf-8 -*-
""" Validation of GraphQL (query) documents.

- Use `validate_ast` to confirm that a GraphQL document is correct.
- This only validates query documents not SDL documents.
- Each validator is a custom vistor which checks one semantic rule defined by
  the spec. They do not cross reference each other and assume that the others
  validators are passing though they should not break and just silently ignore
  unexpected input (if that's not the case, that's a bug).
- There is no suggestion list implementation like the ref implementation
  provides.
"""

# flake8: noqa

from .validate import ValidationResult, validate_ast, SPECIFIED_RULES
from .visitors import ValidationVisitor, VariablesCollector
