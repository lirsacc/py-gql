# -*- coding: utf-8 -*-
from typing import cast

import pytest

from py_gql.schema import (
    ID,
    Argument,
    Field,
    InputField,
    InputObjectType,
    Int,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
    UnionType,
)


@pytest.fixture
def schema() -> Schema:
    Object = InterfaceType("Object", fields=[Field("id", NonNullType(ID))])

    Person = ObjectType(
        "Person",
        fields=[
            Field("id", NonNullType(ID)),
            Field("name", NonNullType(String)),
            Field("pets", NonNullType(ListType(lambda: Animal))),
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

    schema._replace_types_and_directives({"Object": NewObject})

    assert (
        cast(ObjectType, schema.get_type("Person")).interfaces[0]
        is cast(ObjectType, schema.get_type("Animal")).interfaces[0]
        is schema.types["Object"]
        is NewObject
    )


def test_replace_type_in_union(schema: Schema) -> None:
    NewPerson = ObjectType(
        "Person",
        fields=(
            list(cast(ObjectType, schema.types["Person"]).fields)
            + [Field("last_name", NonNullType(String))]
        ),
        interfaces=[cast(InterfaceType, schema.types["Object"])],
    )

    schema._replace_types_and_directives({"Person": NewPerson})

    assert cast(ObjectType, schema.get_type("Person")) is NewPerson

    union_type = cast(UnionType, schema.get_type("LivingBeing"))

    assert NewPerson in union_type.types
    assert 2 == len(union_type.types)


def test_replace_query_type(schema: Schema) -> None:
    NewQuery = ObjectType("Query", fields=[Field("some_number", Int)])
    schema._replace_types_and_directives({"Query": NewQuery})
    assert schema.query_type is NewQuery


def test_replace_mutation_type(schema: Schema) -> None:
    NewMutation = ObjectType(
        "Mutation", fields=[Field("update_some_number", Int)],
    )
    schema._replace_types_and_directives({"Mutation": NewMutation})
    assert schema.mutation_type is NewMutation


def test_root_type_is_not_created(schema: Schema) -> None:
    Subscription = ObjectType(
        "Subscription", fields=[Field("some_number", Int)]
    )
    schema._replace_types_and_directives({"Subscription": Subscription})
    assert schema.subscription_type is None
