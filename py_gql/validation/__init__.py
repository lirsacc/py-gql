# -*- coding: utf-8 -*-
""" Validation of GraphQL (query) documents.

Note:
    This module is only concerned with validating query documents, not SDL
    documents.

.. autoattribute:: py_gql.validation.SPECIFIED_RULES
    :annotation:

    This is the list of :class:`~py_gql.validation.ValidationVisitor`
    from :mod:`py_gql.validation.rules` encoding all the validation rules
    defined in `this section
    <http://facebook.github.io/graphql/June2018/#sec-Validation>`_ of the Spec.
"""

# flake8: noqa

from .validate import ValidationResult, validate_ast, SPECIFIED_RULES
from .visitors import ValidationVisitor, VariablesCollector

__all__ = (
    "ValidationResult",
    "validate_ast",
    "SPECIFIED_RULES",
    "ValidationVisitor",
    "VariablesCollector",
)
