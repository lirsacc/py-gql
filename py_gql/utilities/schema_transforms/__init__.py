# -*- coding: utf-8 -*-
"""Common utilities used to transform GraphQL schemas."""

from ...schema import Schema, SchemaVisitor
from .camel_case import CamelCaseSchemaTransform
from .visibility import VisibilitySchemaTransform


def transform_schema(schema: Schema, *transforms: SchemaVisitor) -> Schema:
    """Apply one or more transformations to a schema instance.

    To prevent accidental side effects, this functions creates a deep clone of
    the schema before applying any transformer.
    """

    updated = schema.clone()

    for t in transforms:
        updated = t.on_schema(updated)

    updated.validate()
    return updated


__all__ = (
    "transform_schema",
    "VisibilitySchemaTransform",
    "CamelCaseSchemaTransform",
)
