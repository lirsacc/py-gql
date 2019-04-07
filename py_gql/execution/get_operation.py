# -*- coding: utf-8 -*-

from typing import Optional

from ..exc import InvalidOperationError
from ..lang import ast as _ast


def get_operation(
    document: _ast.Document, operation_name: Optional[str] = None
) -> _ast.OperationDefinition:
    """ Extract relevant operation from a parsed document.

    In case the ``operation_name`` argument is null, the document is
    expected to contain only one operation which will be extracted.

    Args:
        document: Parsed document
        opeation_name: Operation to extract

    Returns: Relevant operation definition

    Raises:
        :py:class:`ValueError`: No relevant operation can be found.
    """
    operations = [
        definition
        for definition in document.definitions
        if isinstance(definition, _ast.OperationDefinition)
    ]

    if not operations:
        raise InvalidOperationError(
            "Expected at least one operation definition"
        )

    if not operation_name:
        if len(operations) == 1:
            return operations[0]
        raise InvalidOperationError(
            "Operation name is required when document "
            "contains multiple operation definitions"
        )

    for operation in operations:
        if operation.name and operation.name.value == operation_name:
            return operation

    raise InvalidOperationError(
        'No operation "%s" in document' % operation_name
    )
