# -*- coding: utf-8 -*-
from typing import Optional, cast

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
            return self._schema.get_type(
                cast(NamedType, original).name, cast(NamedType, original)
            )

    def visit_schema(self, schema: Schema) -> Schema:
        return super().visit_schema(schema)

    def visit_object(self, object_type: ObjectType) -> Optional[ObjectType]:
        updated = super().visit_object(object_type)
        if updated is not None:
            updated.interfaces = [
                cast(InterfaceType, self._healed(i)) for i in updated.interfaces
            ]
        return updated

    def visit_field(self, field: Field) -> Optional[Field]:
        updated = super().visit_field(field)
        if updated is not None:
            updated.type = self._healed(updated.type)
        return updated

    def visit_argument(self, argument: Argument) -> Optional[Argument]:
        updated = super().visit_argument(argument)
        if updated is not None:
            updated.type = self._healed(updated.type)
        return updated

    def visit_union(self, union: UnionType) -> Optional[UnionType]:
        updated = super().visit_union(union)
        if updated is not None:
            updated.types = [
                cast(ObjectType, self._healed(i)) for i in updated.types
            ]
        return updated

    def visit_input_field(self, field: InputField) -> Optional[InputField]:
        updated = super().visit_input_field(field)
        if updated is not None:
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
    return _HealSchemaVisitor(schema).visit_schema(schema)
