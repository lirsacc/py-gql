# -*- coding: utf-8 -*-
"""
Additional scalar types which are not part of the specification.

These types are provided for convenience as they are pretty common as well as
to serve as examples for how to implement custom Scalar types.

They won't always be supported by GraphQL servers and may not fit every purpose.
They **must** be included in the schema manually either by providing them to
:func:`~py_gql.build_schema` or including them in your type definitions.
"""

import json
import re
import uuid
from base64 import b64decode, b64encode
from typing import Any, Callable, Optional, Pattern, Union

from py_gql import _date_utils as _du
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
        parse: Callable[[str], Any],
        serialize: Callable[[Any], str],
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


class RegexType(StringType):
    """
    ScalarType type class used to validate regex patterns.

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


#: The ``UUID`` scalar type represents a UUID as specified in :rfc:`4122` using
#: Python's :py:mod:`uuid` module.
UUID = StringType(
    "UUID",
    serialize=_serialize_uuid,
    parse=_parse_uuid,
    description=(
        "The `UUID` scalar type represents a UUID as specified in [RFC 4122]"
        "(https://tools.ietf.org/html/rfc4122)"
    ),
)


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


#: The ``JSONString`` scalar type represents any value serializable as JSON
#: using Python's :py:mod:`json` module. This allows opting out of GraphQL's
#: type safety and should be used sparingly.
JSONString = StringType(
    "JSONString",
    serialize=_to_json,
    parse=json.loads,
    description=(
        "The `JSONString` scalar type represents any value serializable as JSON"
    ),
)


#: The ``DateTime`` scalar type represents a datetime value as specified
#: by the `ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_ standard.
#: This expects and parses values as :py:class:`datetime.datetime` objects.
DateTime = StringType(
    "DateTime",
    description=(
        "The `DateTime` scalar type represents a datetime value as specified "
        "by the [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) standard."
    ),
    serialize=_du.serialize_datetime,
    parse=_du.parse_datetime,
)

#: The ``Date`` scalar type represents a date value as specified
#: by the `ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_ standard.
#: This expects and parses values as :py:class:`datetime.date` objects.
Date = StringType(
    "Date",
    description=(
        "The `Date` scalar type represents a date value as specified "
        "by the [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) standard."
    ),
    serialize=_du.serialize_date,
    parse=_du.parse_date,
)

#: The ``Time`` scalar type represents a time value as specified
#: by the `ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_ standard.
#: This expects and parses values as :py:class:`datetime.time` objects.
Time = StringType(
    "Time",
    description=(
        "The `Time` scalar type represents a time value as specified "
        "by the [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) standard."
    ),
    serialize=_du.serialize_time,
    parse=_du.parse_time,
)


def _parse_b64(value: str) -> str:
    return b64decode(value.encode("utf8")).decode("utf8")


def _serialize_b64(value: str) -> str:
    return b64encode(value.encode("utf8")).decode("utf8")


#: Base64 encoded strings suitable to transmit binary data which cannot normally
#: be encoded in a GraphQL String. This uses Python's :py:mod:`base64` module.
Base64String = StringType(
    "Base64String",
    description=(
        "The ``Base64String`` scalar represent strings that have been encoded "
        "using base 64 as specified in "
        "[RFC 3548](https://tools.ietf.org/html/rfc3548.html)."
    ),
    parse=_parse_b64,
    serialize=_serialize_b64,
)


__all__ = (
    "StringType",
    "RegexType",
    "UUID",
    "JSONString",
    "DateTime",
    "Date",
    "Time",
    "Base64String",
)
