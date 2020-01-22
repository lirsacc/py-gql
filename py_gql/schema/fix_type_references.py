# -*- coding: utf-8 -*-
from typing import cast

from .._utils import map_and_filter
from .schema import Schema
from .schema_visitor import Optional, SchemaVisitor
from .types import (
    Argument,
    Field,
    GraphQLType,
    InputField,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    UnionType,
)


class _HealSchemaVisitor(SchemaVisitor):
    def __init__(self, schema: Schema):
        self._schema = schema

    def _healed(self, original: GraphQLType) -> Optional[GraphQLType]:
        if isinstance(original, NonNullType):
            inner = self._healed(original.type)
            return NonNullType(inner) if inner is not None else None
        elif isinstance(original, ListType):
            inner = self._healed(original.type)
            return ListType(inner) if inner is not None else None
        else:
            return self._schema.types.get(cast(NamedType, original).name, None)

    def on_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        updated = cast(ObjectType, super().on_object(object_type))
        updated.interfaces = map_and_filter(
            self._healed, updated.interfaces  # type: ignore
        )
        return updated

    def on_field(self, field: Field) -> Optional[Field]:
        updated = cast(Field, super().on_field(field))
        new_type = self._healed(updated.type)

        if new_type is None:
            return None

        updated.type = new_type
        return updated

    def on_argument(self, argument: Argument) -> Optional[Argument]:
        updated = cast(Argument, super().on_argument(argument))
        new_type = self._healed(updated.type)

        if new_type is None:
            return None

        updated.type = new_type
        return updated

    def on_union(self, union: UnionType) -> Optional[UnionType]:
        updated = cast(UnionType, super().on_union(union))
        updated.types = map_and_filter(
            self._healed, updated.types  # type: ignore
        )
        return updated

    def on_input_field(self, field: InputField) -> Optional[InputField]:
        updated = cast(InputField, super().on_input_field(field))
        new_type = self._healed(updated.type)

        if new_type is None:
            return None

        updated.type = new_type
        return updated


def fix_type_references(schema: Schema) -> Schema:
    """
    Ensure internal representation of types match the ones in the schema's top
    level type map.

    This is useful after modifying a schema inline where a type may have
    swapped out but not all of its forward references (e.g. arguments, fields,
    union, etc.) were.
    """
    # WARN: This will lead to recursive calls until no type needs to be updated
    # through on_schema calling Schema._replace_types_and_directives which
    # calls fix_type_references.
    return _HealSchemaVisitor(schema).on_schema(schema)
