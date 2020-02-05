# -*- coding: utf-8 -*-
"""
Validation of GraphQL (query) documents.

Note:
    This module is only concerned with validating query documents, not SDL
    documents which are validated when using `py_gql.build_schema` or
    :meth:`py_gql.schema.Schema.validate`.
"""

# flake8: noqa

from .validate import (
    SPECIFIED_RULES,
    ValidationResult,
    default_validator,
    validate_ast,
    Validator,
)
from .visitors import ValidationVisitor, VariablesCollector

__all__ = (
    "validate_ast",
    "default_validator",
    "ValidationResult",
    "ValidationVisitor",
    "VariablesCollector",
    "Validator",
    "SPECIFIED_RULES",
)
