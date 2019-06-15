# -*- coding: utf-8 -*-

from typing import Dict, Iterable, List, Optional

from ..exc import SchemaError
from .types import (
    Directive,
    GraphQLType,
    InputObjectType,
    InterfaceType,
    NamedType,
    ObjectType,
    UnionType,
    unwrap_type,
)


def build_type_map(
    types: Iterable[Optional[GraphQLType]],
    directives: Optional[Iterable[Directive]] = None,
    _type_map: Optional[Dict[str, NamedType]] = None,
) -> Dict[str, NamedType]:
    """
    Recursively build a mapping name <> Type from a list of types to include
    all referenced types.

    Warning:
        This will flatten all lazy type definitions and attributes.

    Args:
        types: List of types
        _type_map: Pre-built type map (used for recursive calls)
    """
    type_map = (
        _type_map if _type_map is not None else {}
    )  # type: Dict[str, NamedType]

    for type_ in types:

        if type_ is None:
            continue

        child_types = []  # type: List[GraphQLType]

        type_ = unwrap_type(type_)

        if not isinstance(type_, NamedType):
            raise SchemaError(
                'Expected NamedType but got "%s" of type %s'
                % (type_, type(type_))
            )

        name = type_.name

        if name in type_map:
            if type_ is not type_map[name]:
                raise SchemaError('Duplicate type "%s"' % name)
            continue

        type_map[name] = type_

        if isinstance(type_, UnionType):
            child_types.extend(type_.types)

        if isinstance(type_, ObjectType):
            child_types.extend(type_.interfaces)

        if isinstance(type_, (ObjectType, InterfaceType)):
            for field in type_.fields:
                child_types.append(field.type)
                child_types.extend([arg.type for arg in field.arguments or []])

        if isinstance(type_, InputObjectType):
            for input_field in type_.fields:
                child_types.append(input_field.type)

        type_map.update(build_type_map(child_types, _type_map=type_map))

    if directives:
        directive_types = []  # type: List[GraphQLType]
        for directive in directives:
            directive_types.extend(
                [arg.type for arg in directive.arguments or []]
            )

        type_map.update(build_type_map(directive_types, _type_map=type_map))

    return type_map
