# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional

from ..exc import ValidationError
from ..lang.ast import Document, Field, OperationDefinition
from ..schema import Schema
from .collect_fields import selected_fields


class MaxDepthValidationRule:
    """Validate that a given document doesn't exceed a given query depth.

    Query depth is calculated as nesting levels into object types, traversing
    fragments. For example, given the following document:

    .. code-block:: graphql

        {
            hero {
                name
                friends {
                    ... friendsData
                }
            }
        }

        fragment friendsData on Character {
            friends {
                name
                friends {
                    name
                }
            }
        }

    the depth of the query would be 4.


    Args:
        max_depth: Depth limit (inclusive).
        operation_name: If set this will only consider the operation matching the
            provided name, if not this will collect errors for all operation
            definitions.
    """

    def __init__(self, max_depth: int, *, operation_name: Optional[str] = None):
        self.max_depth = max_depth
        self.operation_name = operation_name

    def __call__(
        self,
        schema: Schema,
        doc: Document,
        variables: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationError]:

        fragments = doc.fragments
        variables = variables or {}

        depth = None  # type: Optional[int]
        errors = []  # type: List[ValidationError]

        for op in doc.definitions:
            if not isinstance(op, OperationDefinition):
                continue

            if self.operation_name and not (
                op.name and op.name.value == self.operation_name
            ):
                continue

            paths = (
                p
                for f in op.selection_set.selections
                if isinstance(f, Field)
                for p in selected_fields(
                    f, fragments=fragments, variables=variables, maxdepth=None,
                )
            )

            depth = max(x.count("/") + 1 for x in paths)

            if depth > self.max_depth:
                errors.append(
                    ValidationError(
                        'Operation "%s" depth (%s) exceeds maximum depth (%s)'
                        % (
                            op.name.value if op.name else "<ANONYMOUS>",
                            depth,
                            self.max_depth,
                        ),
                        nodes=[op],
                    ),
                )

        return errors
