# -*- coding: utf-8 -*-
"""
Common utilities used to transform GraphQL documents.
"""

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
