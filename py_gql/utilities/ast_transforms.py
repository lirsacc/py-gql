# -*- coding: utf-8 -*-
"""
Common utilities used to transform GraphQL documents.
"""

from .._string_utils import camelcase_to_snakecase, snakecase_to_camelcase
from ..lang.ast import Field
from ..lang.visitor import DispatchingVisitor


class RemoveFieldAliasesVisitor(DispatchingVisitor):
    """
    Visitor implementation which removes aliases from output fields.
    """

    def enter_field(self, field: Field) -> Field:
        if field.alias is not None:
            field.alias = None
        return field


class CamelCaseToSnakeCaseVisitor(DispatchingVisitor):
    """
    Visitor implementation which renames field from camelCase to snake_case.

    This is useful when working between languages with different conventions
    such as Python and Javascript.

    Note:
        This only work on the incoming document and usually needs to be paired
        with a post-processing step on the client or before sending out the
        response.
    """

    def enter_field(self, field: Field) -> Field:
        field.name.value = camelcase_to_snakecase(field.name.value)
        return field


class SnakeCaseToCamelCaseVisitor(DispatchingVisitor):
    """
    Visitor implementation which renames field from snake_case to camelCase.

    This is useful when working between languages with different conventions
    such as Python and Javascript.

    Note:
        This only work on the incoming document and usually needs to be paired
        with a post-processing step on the client or before sending out the
        response.
    """

    def enter_field(self, field: Field) -> Field:
        field.name.value = snakecase_to_camelcase(field.name.value)
        return field
