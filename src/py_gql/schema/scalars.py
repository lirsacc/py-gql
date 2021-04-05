# -*- coding: utf-8 -*-
"""
Pre-defined scalar types.
"""

from typing import Any, Callable, List, Mapping, Optional, Type, TypeVar, Union

from ..lang import ast as _ast
from .types import ScalarType


T = TypeVar("T")

ScalarValueNode = Union[
    _ast.IntValue,
    _ast.FloatValue,
    _ast.StringValue,
    _ast.BooleanValue,
]

ScalarValue = Union[str, int, float, bool, None]


# Shortcut to generate ``parse_literal`` from a simple
# parsing function by adding node type validation.
def _typed_coerce(
    coerce_: Callable[[ScalarValue], T],
    *types: Type[ScalarValueNode],
) -> Callable[[ScalarValueNode, Mapping[str, Any]], T]:
    def _coerce(node: ScalarValueNode, _variables: Mapping[str, Any]) -> T:
        if type(node) not in types:
            raise TypeError(f"Invalid literal {node.__class__.__name__}")
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


def coerce_int(maybe_int: ScalarValue) -> int:
    """
    Spec compliant int conversion.
    """
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


def coerce_float(maybe_float: ScalarValue) -> float:
    """
    Spec compliant float conversion.
    """
    if maybe_float == "":
        raise ValueError(
            "Float cannot represent non numeric value: (empty string)",
        )
    if maybe_float is None:
        raise ValueError("Float cannot represent non numeric value: None")

    try:
        return float(maybe_float)
    except ValueError:
        raise ValueError(
            f"Float cannot represent non numeric value: {maybe_float}",
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


def _parse_string(value: ScalarValue) -> str:
    if isinstance(value, (list, tuple)):
        raise ValueError(f'String cannot represent list value "{value}"')
    return str(value)


def coerce_string(value: Any) -> str:
    if value in (True, False):
        return str(value).lower()

    if isinstance(value, (list, tuple)):
        raise ValueError(f'String cannot represent list value "{value}"')

    return str(value)


_coerce_string_node = _typed_coerce(_parse_string, _ast.StringValue)


String = ScalarType(
    "String",
    description=(
        "The `String` scalar type represents textual data, represented as "
        "UTF-8 character sequences. The String type is most often used by "
        "GraphQL to represent free-form human-readable text."
    ),
    serialize=coerce_string,
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


def _identity(value: T) -> T:
    return value


def default_scalar(
    name: str,
    description: Optional[str] = None,
    nodes: Optional[
        List[Union[_ast.ScalarTypeDefinition, _ast.ScalarTypeExtension]]
    ] = None,
) -> ScalarType:
    """
    Create a default transparent scalar type.

    This should be used as a stand in for custom scalar when the exact
    implementation is not known (e.g. when generating a schema). Values will be
    serialised and parsed as is without any validation.
    """
    return ScalarType(
        name,
        serialize=_identity,
        parse=_identity,
        parse_literal=lambda node, _: node.value,
        description=description,
        nodes=nodes,
    )
