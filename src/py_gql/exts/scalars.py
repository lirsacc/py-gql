# -*- coding: utf-8 -*-
"""
Additional, non specified scalar types and utilities to build your own
scalar types.
"""

import re
import uuid
from typing import Any, Callable, Optional, Pattern, Union

from py_gql.exc import ScalarParsingError
from py_gql.lang import ast
from py_gql.schema.scalars import ScalarValue, ScalarValueNode, coerce_string
from py_gql.schema.types import ScalarType


class StringType(ScalarType):
    """
    Helper class to define custom String type.

    The resulting types will only accept String nodes.
    """

    def __init__(
        self,
        name: str,
        parse: Callable[[str], Any] = lambda x: x,
        serialize: Callable[[Any], str] = lambda x: str(x),
        description: Optional[str] = None,
    ):
        super().__init__(
            name,
            serialize=serialize,
            parse=parse,  # type: ignore
            parse_literal=None,
            description=description,
        )

    def parse_literal(
        self, node: ScalarValueNode, variables: Optional[Any] = None,
    ) -> Any:
        if not isinstance(node, ast.StringValue):
            raise ScalarParsingError(
                "Invalid literal %s" % node.__class__.__name__, [node]
            )
        return self.parse(node.value)


def _parse_uuid(maybe_uuid: ScalarValue) -> uuid.UUID:
    if isinstance(maybe_uuid, str):
        return uuid.UUID(maybe_uuid)

    raise TypeError(type(maybe_uuid))


def _serialize_uuid(maybe_uuid: Union[str, uuid.UUID]) -> str:
    if isinstance(maybe_uuid, uuid.UUID):
        return str(maybe_uuid)
    elif isinstance(maybe_uuid, str):
        return str(uuid.UUID(maybe_uuid))

    raise TypeError(type(maybe_uuid))


UUID = StringType(
    "UUID",
    serialize=_serialize_uuid,
    parse=_parse_uuid,
    description=(
        "The `UUID` scalar type represents a UUID as specified in [RFC 4122]"
        "(https://tools.ietf.org/html/rfc4122)"
    ),
)


class RegexType(StringType):
    """
    ScalarType type base clasee used to validate regex patterns.

    This will accept either a string or a compiled Pattern and will match
    strings both on output and input values.

    Args:
        name: Type name
        regex: Regular expression
        description: Type description

    Attributes:
        name (str): Type name
        description (str): Type description
    """

    def __init__(
        self,
        name: str,
        regex: Union[str, Pattern[str]],
        description: Optional[str] = None,
    ):

        if isinstance(regex, str):
            self._regex = re.compile(regex)
        else:
            self._regex = regex

        if description is None:
            description = "String matching pattern /%s/" % self._regex.pattern

        def _coerce(value: Any) -> str:
            string_value = coerce_string(value)

            if not self._regex.match(string_value):
                raise ValueError(
                    '"%s" does not match pattern "%s"'
                    % (string_value, self._regex.pattern)
                )
            return string_value

        super().__init__(
            name, serialize=_coerce, parse=_coerce, description=description,
        )


__all__ = (
    "StringType",
    "RegexType",
    "UUID",
)
