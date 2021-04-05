# -*- coding: utf-8 -*-

from typing import Optional, Tuple

from ..exc import InvalidOperationError
from ..lang import ast as _ast
from ..schema import ObjectType, Schema


def get_operation(
    document: _ast.Document,
    operation_name: Optional[str] = None,
) -> _ast.OperationDefinition:
    """
    Extract relevant operation from a parsed document.

    In case the ``operation_name`` argument is null, the document is
    expected to contain only one operation which will be extracted.

    Args:
        document: Parsed document
        operation_name: Operation to extract

    Returns:
        Relevant operation definition

    Raises:
        InvalidOperationError: No relevant operation can be found.
    """
    operations = [
        definition
        for definition in document.definitions
        if isinstance(definition, _ast.OperationDefinition)
    ]

    if not operations:
        raise InvalidOperationError(
            "Expected at least one operation definition",
        )

    if not operation_name:
        if len(operations) == 1:
            return operations[0]
        raise InvalidOperationError(
            "Operation name is required when document "
            "contains multiple operation definitions",
        )

    for operation in operations:
        if operation.name and operation.name.value == operation_name:
            return operation

    raise InvalidOperationError(f'No operation "{operation_name}" in document')


def get_operation_with_type(
    schema: Schema,
    document: _ast.Document,
    operation_name: Optional[str] = None,
) -> Tuple[_ast.OperationDefinition, ObjectType]:
    """
    Extract relevant operation from a parsed document and ObjectType.

    Args:
        schema: Schema
        document: Parsed document
        operation_name: Operation to extract

    Returns:
        Relevant operation definition and object type

    Raises:
        InvalidOperationError: when no relevant operation can be found or there
            is no related type.
    """
    operation = get_operation(document, operation_name)

    root_type = {
        "query": schema.query_type,
        "mutation": schema.mutation_type,
        "subscription": schema.subscription_type,
    }[operation.operation]

    if root_type is None:
        raise InvalidOperationError(
            f"Schema doesn't support {operation.operation} operation",
        )

    return operation, root_type
