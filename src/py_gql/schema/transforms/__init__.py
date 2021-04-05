# -*- coding: utf-8 -*-
"""
Common utilities used to transform GraphQL schemas.
"""

import abc
from typing import Optional

from ..._string_utils import snakecase_to_camelcase
from ...schema import Argument, Field, InputField, Schema, SchemaVisitor
from .visibility import VisibilitySchemaTransform


def transform_schema(schema: Schema, *transforms: SchemaVisitor) -> Schema:
    """
    Apply one or more transformations to a schema instance.

    To prevent accidental side effects, this functions creates a deep clone of
    the schema before applying any transformer.
    """
    updated = schema.clone()

    for t in transforms:
        updated = t.on_schema(updated)

    updated.validate()
    return updated


class CaseSchemaTransform(abc.ABC, SchemaVisitor):
    """
    Systematically expose a different name for object that support ``python_name``.

    This transform can be implemented to systematically expose a different name
    for field and directive arguments, fields and input fields. No other object
    is touched and descriptions are not modified.
    """

    @abc.abstractmethod
    def transform(self, value: str) -> str:
        raise NotImplementedError()

    def on_argument(self, arg: Argument) -> Optional[Argument]:
        return super().on_argument(
            Argument(
                self.transform(arg.name),
                arg.type,
                default_value=arg._default_value,
                description=arg.description,
                node=arg.node,
                python_name=arg.python_name,
            ),
        )

    def on_input_field(self, input_field: InputField) -> Optional[InputField]:
        return super().on_input_field(
            InputField(
                self.transform(input_field.name),
                input_field.type,
                default_value=input_field._default_value,
                description=input_field.description,
                node=input_field.node,
                python_name=input_field.python_name,
            ),
        )

    def on_field(self, field: Field) -> Optional[Field]:
        return super().on_field(
            Field(
                self.transform(field.name),
                field.type,
                args=field.arguments,
                resolver=field.resolver,
                subscription_resolver=field.subscription_resolver,
                description=field.description,
                deprecation_reason=field.deprecation_reason,
                node=field.node,
                python_name=field.python_name,
            ),
        )


class CamelCaseSchemaTransform(CaseSchemaTransform):
    """
    Rename schema elements to camel case from Python's snake case convention.

    This is a common convention in GraphQL projects which are usually consumed
    by web clients written in Javascript where camel case is the standard
    convention.

    This transform will rename field and directive argument names, field names,
    and input field names. It won't touch any enum value or type name and won't
    update descriptions.

    Warning:
        This is only guaranteed to convert ``snake_case`` to ``camelCase`` and
        not arbitrary case (e.g. ``dash-case`` will not be converted).
    """

    def transform(self, value: str) -> str:
        return snakecase_to_camelcase(value)


__all__ = (
    "transform_schema",
    "VisibilitySchemaTransform",
    "CaseSchemaTransform",
    "CamelCaseSchemaTransform",
)
