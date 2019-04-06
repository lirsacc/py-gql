# -*- coding: utf-8 -*-
from typing import cast

from .schema import Schema
from .schema_visitor import SchemaVisitor
from .types import (
    Argument,
    Field,
    GraphQLType,
    InputField,
    InterfaceType,
    ListType,
    NamedType,
    NonNullType,
    ObjectType,
    UnionType,
)


class _HealSchemaVisitor(SchemaVisitor):
    def __init__(self, schema: Schema):
        self._schema = schema

    def _healed(self, original: GraphQLType) -> GraphQLType:
        if isinstance(original, NonNullType):
            return NonNullType(self._healed(original.type))
        elif isinstance(original, ListType):
            return ListType(self._healed(original.type))
        else:
            return self._schema.types.get(
                cast(NamedType, original).name, cast(NamedType, original)
            )

    def on_object(self, object_type: ObjectType) -> ObjectType:
        updated = cast(ObjectType, super().on_object(object_type))
        updated.interfaces = [
            cast(InterfaceType, self._healed(i)) for i in updated.interfaces
        ]
        return updated

    def on_field_definition(self, field: Field) -> Field:
        updated = cast(Field, super().on_field_definition(field))
        updated.type = self._healed(updated.type)
        return updated

    def on_argument_definition(self, argument: Argument) -> Argument:
        updated = cast(Argument, super().on_argument_definition(argument))
        updated.type = self._healed(updated.type)
        return updated

    def on_union(self, union: UnionType) -> UnionType:
        updated = cast(UnionType, super().on_union(union))
        updated.types = [
            cast(ObjectType, self._healed(i)) for i in updated.types
        ]
        return updated

    def on_input_field_definition(self, field: InputField) -> InputField:
        updated = cast(InputField, super().on_input_field_definition(field))
        updated.type = self._healed(updated.type)
        return updated


def fix_type_references(schema: Schema) -> Schema:
    """
    Ensure internal representation of types match the ones in the schema's top
    level type map.

    This is useful after modifying a schema inline where a type may have
    swapped out but not all of its forward references (e.g. arguments, fields,
    union, etc.) were.
    """
    return _HealSchemaVisitor(schema).on_schema(schema)
