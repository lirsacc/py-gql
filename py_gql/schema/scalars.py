# -*- coding: utf-8 -*-
""" Pre-defined scalar types """

import re
import uuid
from typing import Any, Callable, List, Mapping, Optional, Type, TypeVar, Union

from ..lang import ast as _ast
from .types import ScalarType

T = TypeVar("T")

_ScalarValueNode = Union[
    _ast.IntValue, _ast.FloatValue, _ast.StringValue, _ast.BooleanValue
]


# Shortcut to generate ``parse_literal`` from a simple
# parsing function by adding node type validation.
def _typed_coerce(
    coerce_: Callable[[Any], T], *types: Type[_ScalarValueNode]
) -> Callable[[_ScalarValueNode, Mapping[str, Any]], T]:
    def _coerce(node: _ScalarValueNode, _variables: Mapping[str, Any]) -> T:
        if type(node) not in types:
            raise TypeError("Invalid literal %s" % node.__class__.__name__)
        return coerce_(node.value)

    return _coerce


_coerce_bool_node = _typed_coerce(bool, _ast.BooleanValue)


Boolean = ScalarType(
    "Boolean",
    description="The `Boolean` scalar type represents `true` or `false`.",
    serialize=bool,
    parse=bool,
    parse_literal=_coerce_bool_node,
)


# Spec says -2^31 to 2^31... use floats to get larger numbers.
MAX_INT = 2147483647
MIN_INT = -2147483648
INVALID_INT = "Int cannot represent non integer value: %s"
INVALID_NUMERIC = "Int cannot represent non 32-bit signed integer: %s"


def coerce_int(maybe_int: Any) -> int:
    """ Spec compliant int conversion. """

    if isinstance(maybe_int, int):
        numeric = maybe_int
    elif isinstance(maybe_int, float):
        numeric = int(maybe_int)
        if numeric != maybe_int:
            raise ValueError(INVALID_INT % maybe_int)
    elif maybe_int is None:
        raise ValueError(INVALID_INT % "None")
    elif isinstance(maybe_int, str):
        if not maybe_int:
            raise ValueError(INVALID_INT % "(empty string)")
        try:
            numeric = int(maybe_int, 10)
        except ValueError:
            try:
                float_value = float(maybe_int)
                if float_value.is_integer():
                    numeric = int(float_value)
                else:
                    raise ValueError(INVALID_NUMERIC % maybe_int)
            except (OverflowError, ValueError):
                raise ValueError(INVALID_INT % maybe_int)
    else:
        raise ValueError(INVALID_INT, repr(maybe_int))

    if not (MIN_INT < numeric < MAX_INT):
        raise ValueError(INVALID_NUMERIC % maybe_int)

    return numeric


def coerce_float(maybe_float: Any) -> float:
    """ Spec compliant float conversion. """
    if maybe_float == "":
        raise ValueError(
            "Float cannot represent non numeric value: (empty string)"
        )
    if maybe_float is None:
        raise ValueError("Float cannot represent non numeric value: None")

    try:
        return float(maybe_float)
    except ValueError:
        raise ValueError(
            "Float cannot represent non numeric value: %s" % maybe_float
        )


_coerce_int_node = _typed_coerce(coerce_int, _ast.IntValue)
_coerce_float_node = _typed_coerce(coerce_float, _ast.FloatValue, _ast.IntValue)


Int = ScalarType(
    "Int",
    description=(
        "The `Int` scalar type represents non-fractional signed whole numeric "
        "values. Int can represent values between -(2^31) and 2^31 - 1."
    ),
    serialize=coerce_int,
    parse=coerce_int,
    parse_literal=_coerce_int_node,
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
    parse_literal=_coerce_float_node,
)


def _parse_string(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        raise ValueError('String cannot represent list value "%s"' % value)
    return str(value)


def _serialize_string(value: Any) -> str:
    if value in (True, False):
        return str(value).lower()
    return _parse_string(value)


_coerce_string_node = _typed_coerce(_parse_string, _ast.StringValue)


String = ScalarType(
    "String",
    description=(
        "The `String` scalar type represents textual data, represented as "
        "UTF-8 character sequences. The String type is most often used by "
        "GraphQL to represent free-form human-readable text."
    ),
    serialize=_serialize_string,
    parse=_parse_string,
    parse_literal=_coerce_string_node,
)  # type: ScalarType

_coerce_id_node = _typed_coerce(str, _ast.StringValue, _ast.IntValue)


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
    serialize=str,
    parse=str,
    parse_literal=_coerce_id_node,
)


# These are the types which are part of the spec and will always be available
# in any spec compliant GraphQL server.
SPECIFIED_SCALAR_TYPES = (Int, Float, Boolean, String, ID)

# Further down are common types for your convenience but which will 1) not
# be available by default 2) not be available in other GraphQL servers a-priori.


def _serialize_uuid(maybe_uuid: Any) -> str:
    if isinstance(maybe_uuid, uuid.UUID):
        return str(maybe_uuid)
    else:
        return str(uuid.UUID(maybe_uuid))


def _parse_uuid(maybe_uuid: Any) -> uuid.UUID:
    if isinstance(maybe_uuid, uuid.UUID):
        return maybe_uuid
    return uuid.UUID(maybe_uuid)


_coerce_uuid_node = _typed_coerce(_parse_uuid, _ast.StringValue)


UUID = ScalarType(
    "UUID",
    description=(
        "The `UUID` scalar type represents a UUID as specified in [RFC 4122]"
        "(https://tools.ietf.org/html/rfc4122)"
    ),
    serialize=_serialize_uuid,
    parse=_parse_uuid,
    parse_literal=_coerce_uuid_node,
)


class RegexType(ScalarType):
    """
    Scalar typeclass to validate regex patterns.

    Args:
        name: Type name
        regex: Regular expression
        description: Type description

    Attributes:
        name (str): Type name
        description (str): Type description
    """

    def __init__(self, name, regex, description=None):

        if isinstance(regex, str):
            self._regex = re.compile(regex)
        else:
            self._regex = regex

        if description is None:
            description = "String matching pattern /%s/" % self._regex.pattern

        def _parse(value: Any) -> str:
            string_value = _serialize_string(value)
            if not self._regex.match(string_value):
                raise ValueError(
                    '"%s" does not match pattern "%s"'
                    % (string_value, self._regex.pattern)
                )
            return string_value

        _parse_node = _typed_coerce(_parse, _ast.StringValue)

        super(RegexType, self).__init__(
            name,
            serialize=_parse,
            parse=_parse,
            parse_literal=_parse_node,
            description=description,
        )


def _identity(value: T) -> T:
    return value


def default_scalar(
    name: str,
    description: Optional[str] = None,
    nodes: Optional[
        List[Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension]]
    ] = None,
) -> ScalarType:
    """ Default noop scalar types used when generating scalars from schema
    definitions. """
    return ScalarType(
        name,
        serialize=_identity,
        parse=_identity,
        parse_literal=lambda node, _: node.value,
        description=description,
        nodes=nodes,
    )
