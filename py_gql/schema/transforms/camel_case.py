# -*- coding: utf-8 -*-
from typing import Optional

from ..._string_utils import snakecase_to_camelcase
from ...schema import Argument, Field, InputField, SchemaVisitor


class CamelCaseSchemaTransform(SchemaVisitor):
    """Rename schema elements to camel case from the usual snake case convention
    found in Python code.

    This is a common convention in GraphQL projects which are usually consumed
    by web clients written in Javascript where camel case is the standard
    convention.

    This transofm will rename field and directive argument names, field names,
    and input field names. It won't touch any enum value or type name and won't
    replace the values in the description.
    """

    def on_argument(self, arg: Argument) -> Optional[Argument]:
        return super().on_argument(
            Argument(
                snakecase_to_camelcase(arg.name),
                arg.type,
                default_value=arg._default_value,
                description=arg.description,
                node=arg.node,
                python_name=arg.python_name,
            )
        )

    def on_input_field(self, input_field: InputField) -> Optional[InputField]:
        return super().on_input_field(
            InputField(
                snakecase_to_camelcase(input_field.name),
                input_field.type,
                default_value=input_field._default_value,
                description=input_field.description,
                node=input_field.node,
                python_name=input_field.python_name,
            )
        )

    def on_field(self, field: Field) -> Optional[Field]:
        return super().on_field(
            Field(
                snakecase_to_camelcase(field.name),
                field.type,
                args=field.arguments,
                resolver=field.resolver,
                subscription_resolver=field.subscription_resolver,
                description=field.description,
                deprecation_reason=field.deprecation_reason,
                node=field.node,
                python_name=field.python_name,
            )
        )
