# -*- coding: utf-8 -*-
from typing import cast

import pytest

from py_gql.schema import (
    ID,
    Argument,
    Field,
    InputField,
    InputObjectType,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
    UnionType,
)

# NOTE: fix_type_reference is tested through Schema._replace_types_and_directives


@pytest.fixture
def schema() -> Schema:
    Object = InterfaceType("Object", fields=[Field("id", NonNullType(ID))])

    Person = ObjectType(
        "Person",
        fields=[
            Field("id", NonNullType(ID)),
            Field("name", NonNullType(String)),
            Field(
                "pets", NonNullType(ListType(lambda: Animal))  # type: ignore
            ),
        ],
        interfaces=[Object],
    )

    Animal = ObjectType(
        "Animal",
        fields=[
            Field("id", NonNullType(ID)),
            Field("name", NonNullType(String)),
            Field("owner", Person),
        ],
        interfaces=[Object],
    )

    LivingBeing = UnionType("LivingBeing", [Person, Animal])

    CreatePersonInput = InputObjectType(
        "CreatePersonInput",
        [InputField("id", ID), InputField("name", NonNullType(String))],
    )

    return Schema(
        query_type=ObjectType(
            "Query",
            fields=[
                Field("person", Person, args=[Argument("id", ID)]),
                Field("pet", Animal, args=[Argument("id", ID)]),
                Field("living_being", LivingBeing, args=[Argument("id", ID)]),
            ],
        ),
        mutation_type=ObjectType(
            "Mutation", fields=[Field("createPerson", CreatePersonInput)]
        ),
    )


def test_replace_interface_in_implementers(schema: Schema) -> None:
    NewObject = InterfaceType(
        "Object",
        fields=[
            Field("id", NonNullType(ID)),
            Field("name", NonNullType(String)),
        ],
    )

    schema._replace_types_and_directives([NewObject])

    assert (
        cast(ObjectType, schema.get_type("Person")).interfaces[0]
        is cast(ObjectType, schema.get_type("Animal")).interfaces[0]
        is schema.types["Object"]
        is NewObject
    )


def test_replace_type_in_union(schema: Schema) -> None:
    NewPerson = ObjectType(
        "Person",
        fields=cast(ObjectType, schema.types["Person"]).fields
        + [Field("last_name", NonNullType(String))],
        interfaces=[cast(InterfaceType, schema.types["Object"])],
    )

    schema._replace_types_and_directives([NewPerson])

    assert cast(ObjectType, schema.get_type("Person")) is NewPerson

    union_type = cast(UnionType, schema.get_type("LivingBeing"))

    assert NewPerson in union_type.types
    assert 2 == len(union_type.types)
