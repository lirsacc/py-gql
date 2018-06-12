# -*- coding: utf-8 -*-
""" Pre-defined scalar types """

import re
import uuid

import six

from ..lang import ast as _ast
from .types import ScalarType


# Shortcut to generate ``parse_literal`` from a simple
# parsing function by adding node type validation.
def _typed_coerce(coerce, *types):
    def _coerce(node, variables):
        if type(node) not in types:
            raise TypeError("Invalid literal %s" % node.__class__.__name__)
        return coerce(node.value)

    return _coerce


Boolean = ScalarType(
    "Boolean",
    description="The `Boolean` scalar type represents `true` or `false`.",
    serialize=bool,
    parse=bool,
    parse_literal=_typed_coerce(bool, _ast.BooleanValue),
    _specififed=True,
)


# Spec says -2^31 to 2^31... use floats to get larger numbers.
MAX_INT = 2147483647
MIN_INT = -2147483648
EXPONENT_RE = re.compile(r"1e\d+")


def coerce_int(maybe_int):
    """ Spec compliant int conversion. """
    if maybe_int == "":
        raise ValueError(
            "Int cannot represent non 32-bit signed integer: (empty string)"
        )

    if maybe_int is None:
        raise ValueError("Int cannot represent non 32-bit signed integer: None")

    if isinstance(maybe_int, six.string_types):
        try:
            if EXPONENT_RE.match(maybe_int):
                numeric = int(float(maybe_int))
            else:
                numeric = int(maybe_int, 10)
        except ValueError:
            raise ValueError("Int cannot represent non-integer value: %s" % maybe_int)
    else:
        numeric = int(maybe_int)
        if numeric != maybe_int:
            raise ValueError("Int cannot represent non-integer value: %s" % maybe_int)

    if not (MIN_INT < numeric < MAX_INT):
        raise ValueError(
            "Int cannot represent non 32-bit signed integer: %s" % maybe_int
        )

    return numeric


def coerce_float(maybe_float):
    """ Spec compliant float conversion. """
    if maybe_float == "":
        raise ValueError("Float cannot represent non numeric value: (empty string)")
    if maybe_float is None:
        raise ValueError("Float cannot represent non numeric value: None")
    try:
        return float(maybe_float)
    except ValueError:
        raise ValueError("Float cannot represent non numeric value: %s" % maybe_float)


Int = ScalarType(
    "Int",
    description=(
        "The `Int` scalar type represents non-fractional signed whole numeric "
        "values. Int can represent values between -(2^31) and 2^31 - 1. "
    ),
    serialize=coerce_int,
    parse=coerce_int,
    parse_literal=_typed_coerce(coerce_int, _ast.IntValue),
    _specififed=True,
)


Float = ScalarType(
    "Float",
    description=(
        "The `Float` scalar type represents signed double-precision "
        "fractional values as specified by "
        "[IEEE 754](http://en.wikipedia.org/wiki/IEEE_floating_point)."
    ),
    serialize=coerce_float,
    parse=coerce_float,
    parse_literal=_typed_coerce(coerce_float, _ast.FloatValue, _ast.IntValue),
    _specififed=True,
)


def _parse_string(value):
    if isinstance(value, (list, tuple)):
        raise ValueError('String cannot represent list value "%s"' % value)
    return six.text_type(value)


def _serialize_string(value):
    if value in (True, False):
        return str(value).lower()
    return _parse_string(value)


String = ScalarType(
    "String",
    description=(
        "The `String` scalar type represents textual data, represented as "
        "UTF-8 character sequences. The String type is most often used by "
        "GraphQL to represent free-form human-readable text."
    ),
    serialize=_serialize_string,
    parse=_parse_string,
    parse_literal=_typed_coerce(_parse_string, _ast.StringValue),
    _specififed=True,
)


ID = ScalarType(
    "ID",
    description=(
        "The `ID` scalar type represents a unique identifier, often used to "
        "refetch an object or as key for a cache. The ID type appears in a "
        "JSON response as a String; however, it is not intended to be "
        "human-readable. When expected as an input type, any string (such "
        'as `"4"`) or integer (such as `4`) input value will be accepted as '
        "an ID."
    ),
    serialize=six.text_type,
    parse=six.text_type,
    parse_literal=_typed_coerce(six.text_type, _ast.StringValue, _ast.IntValue),
    _specififed=True,
)


# These are the types which are part of the spec and will always be available
# in any spec compliant GraphQL server.
SPECIFIED_SCALAR_TYPES = (Int, Float, Boolean, String, ID)

# Further down are common types for your convenience but which will 1) not
# be available by default 2) not be available in other GraphQL servers a-priori.

# [TODO] Port more common types (ISO8601 Datetime, ISO Date, Email, Regex, ...)


def _serialize_uuid(maybe_uuid):
    if isinstance(maybe_uuid, uuid.UUID):
        return str(maybe_uuid)
    else:
        return str(uuid.UUID(maybe_uuid))


def _parse_uuid(maybe_uuid):
    if isinstance(maybe_uuid, uuid.UUID):
        return maybe_uuid
    return uuid.UUID(maybe_uuid)


UUID = ScalarType(
    "UUID",
    description=(
        "The `UUID` scalar type represents a UUID as specified in [RFC 4122]"
        "[https://tools.ietf.org/html/rfc4122]"
    ),
    serialize=_serialize_uuid,
    parse=_parse_uuid,
    parse_literal=_typed_coerce(_parse_uuid, _ast.StringValue),
)


class RegexType(ScalarType):
    """ Build types to validate regex patterns """

    def __init__(self, name, regex, description=None):
        """
        """
        self.name = name

        if isinstance(regex, six.string_types):
            self.regex = re.compile(regex)
        else:
            self.regex = regex

        if description is None:
            self.description = "String matching pattern /%s/" % self.regex.pattern
        else:
            self.description = description

        def _parse(value):
            string_value = _serialize_string(value)
            if not self.regex.match(string_value):
                raise ValueError(
                    '"%s" does not match pattern "%s"'
                    % (string_value, self.regex.pattern)
                )
            return string_value

        self._parse = _parse
        self._serialize = _parse
        self._parse_literal = _typed_coerce(_parse, _ast.StringValue)


class DefaultCustomScalar(ScalarType):
    """ Default string based behaviour for scalar types derived from schema SDL.
    This will be essentially take everything and transform it into a string.
    """

    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        self._serialize = String._serialize
        self._parse = String._parse
        self._parse_literal = _typed_coerce(
            String._parse,
            _ast.StringValue,
            _ast.FloatValue,
            _ast.IntValue,
            _ast.BooleanValue,
        )
