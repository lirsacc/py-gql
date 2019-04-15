# -*- coding: utf-8 -*-
""" execution tests related to abstract types (Interface, Union) """
# pylint: disable = redefined-outer-name

import pytest

from py_gql.schema import (
    Boolean,
    Field,
    InterfaceType,
    ListType,
    ObjectType,
    Schema,
    String,
    UnionType,
)

from ._test_utils import assert_execution

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class Dog:
    def __init__(self, name, woofs):
        self.name = name
        self.woofs = woofs


class Cat:
    def __init__(self, name, meows):
        self.name = name
        self.meows = meows


class Human:
    def __init__(self, name):
        self.name = name


class Person:
    def __init__(self, name, pets, friends):
        self.name = name
        self.pets = pets
        self.friends = friends


async def test_ObjectType_is_type_of_for_interface_runtime_inference(
    executor_cls
):
    PetType = InterfaceType("Pet", [Field("name", String)])

    DogType = ObjectType(
        "Dog",
        [Field("name", String), Field("woofs", Boolean)],
        interfaces=[PetType],
        is_type_of=Dog,
    )  # type: ObjectType

    CatType = ObjectType(
        "Cat",
        [Field("name", String), Field("meows", Boolean)],
        interfaces=[PetType],
        is_type_of=Cat,
    )  # type: ObjectType

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolver=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    await assert_execution(
        schema,
        """{
            pets {
                name
                __typename
                ... on Dog { woofs }
                ... on Cat { meows }
            }
        }""",
        executor_cls=executor_cls,
        expected_data={
            "pets": [
                {"name": "Odie", "woofs": True, "__typename": "Dog"},
                {"name": "Garfield", "meows": False, "__typename": "Cat"},
            ]
        },
    )


async def test_ObjectType_is_type_of_for_union_runtime_inference(executor_cls):
    DogType = ObjectType(
        "Dog", [Field("name", String), Field("woofs", Boolean)], is_type_of=Dog
    )

    CatType = ObjectType(
        "Cat", [Field("name", String), Field("meows", Boolean)], is_type_of=Cat
    )

    PetType = UnionType("Pet", [DogType, CatType])

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolver=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    await assert_execution(
        schema,
        """{
            pets {
                __typename
                ... on Dog { woofs, name }
                ... on Cat { meows, name }
            }
        }""",
        executor_cls=executor_cls,
        expected_data={
            "pets": [
                {"name": "Odie", "woofs": True, "__typename": "Dog"},
                {"name": "Garfield", "meows": False, "__typename": "Cat"},
            ]
        },
    )


# WARN: This test will trigger a coroutine never awaited warning as the runtime
# warning short circuits the execution.
async def test_type_resolution_on_interface_yields_useful_error(executor_cls):
    """ Different from ref implementation -> this should never happen
    so we crash """

    def _resolve_pet_type(value):
        return {Dog: DogType, Cat: CatType, Human: HumanType}.get(
            type(value), None
        )

    PetType = InterfaceType(
        "Pet", [Field("name", String)], resolve_type=_resolve_pet_type
    )

    HumanType = ObjectType("Human", [Field("name", String)])

    DogType = ObjectType(
        "Dog",
        [Field("name", String), Field("woofs", Boolean)],
        interfaces=[PetType],
    )

    CatType = ObjectType(
        "Cat",
        [Field("name", String), Field("meows", Boolean)],
        interfaces=[PetType],
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolver=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                        Human("Jon"),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    await assert_execution(
        schema,
        """{
        pets {
            name
            __typename
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        }""",
        executor_cls=executor_cls,
        expected_exc=(
            RuntimeError,
            (
                'Runtime ObjectType "Human" is not a possible type for field '
                '"pets[2]" of type "Pet".'
            ),
        ),
    )


# WARN: This test will trigger a coroutine never awaited warning as the runtime
# warning short circuits the execution.
async def test_type_resolution_on_union_yields_useful_error(executor_cls):
    """ Different from ref implementation -> this should never happen
    so we crash """

    def _resolve_pet_type(value):
        return {Dog: DogType, Cat: CatType, Human: HumanType}.get(
            type(value), None
        )

    HumanType = ObjectType("Human", [Field("name", String)])

    DogType = ObjectType(
        "Dog", [Field("name", String), Field("woofs", Boolean)]
    )

    CatType = ObjectType(
        "Cat", [Field("name", String), Field("meows", Boolean)]
    )

    PetType = UnionType(
        "Pet", [DogType, CatType], resolve_type=_resolve_pet_type
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolver=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                        Human("Jon"),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    await assert_execution(
        schema,
        """{
        pets {
            __typename
            ... on Dog { woofs, name }
            ... on Cat { meows, name }
        }
        }""",
        executor_cls=executor_cls,
        expected_exc=(
            RuntimeError,
            (
                'Runtime ObjectType "Human" is not a possible type for field '
                '"pets[2]" of type "Pet".'
            ),
        ),
    )


async def test_type_resolution_supports_strings(executor_cls):
    def _resolve_pet_type(value):
        return type(value).__name__

    PetType = InterfaceType(
        "Pet", [Field("name", String)], resolve_type=_resolve_pet_type
    )

    DogType = ObjectType(
        "Dog",
        [Field("name", String), Field("woofs", Boolean)],
        interfaces=[PetType],
    )

    CatType = ObjectType(
        "Cat",
        [Field("name", String), Field("meows", Boolean)],
        interfaces=[PetType],
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolver=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    await assert_execution(
        schema,
        """{
        pets {
            name
            __typename
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        }""",
        executor_cls=executor_cls,
    )


async def test_type_resolution_supports_object_attribute(executor_cls):
    PetType = InterfaceType("Pet", [Field("name", String)])

    DogType = ObjectType(
        "Dog",
        [Field("name", String), Field("woofs", Boolean)],
        interfaces=[PetType],
    )

    CatType = ObjectType(
        "Cat",
        [Field("name", String), Field("meows", Boolean)],
        interfaces=[PetType],
    )

    class Dog:
        __typename__ = "Dog"

        def __init__(self, name, woofs):
            self.name = name
            self.woofs = woofs

    class Cat:
        __typename__ = "Cat"

        def __init__(self, name, meows):
            self.name = name
            self.meows = meows

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolver=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    await assert_execution(
        schema,
        """{
        pets {
            name
            __typename
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        }""",
        executor_cls=executor_cls,
    )


NamedType = InterfaceType("Named", [Field("name", String)])

DogType = ObjectType(
    "Dog",
    [Field("name", String), Field("woofs", Boolean)],
    interfaces=[NamedType],
    is_type_of=Dog,
)


CatType = ObjectType(
    "Cat",
    [Field("name", String), Field("meows", Boolean)],
    interfaces=[NamedType],
    is_type_of=Cat,
)


def _resolve_pet_type(value):
    if isinstance(value, Dog):
        return DogType
    elif isinstance(value, Cat):
        return CatType


PetType = UnionType("Pet", [DogType, CatType], resolve_type=_resolve_pet_type)

PersonType = ObjectType(
    "Person",
    [
        Field("name", String),
        Field("pets", ListType(PetType)),
        Field("friends", lambda: ListType(NamedType)),
    ],
    interfaces=[NamedType],
    is_type_of=Person,
)

_SCHEMA = Schema(PersonType)

_GARFIELD = Cat("Garfield", False)
_ODIE = Dog("Odie", True)
_LIZ = Person("Liz", None, None)
_JOHN = Person("John", [_GARFIELD, _ODIE], [_LIZ, _ODIE])


async def test_it_can_introspect_on_union_and_intersection_types(executor_cls):
    await assert_execution(
        _SCHEMA,
        """
        {
            Named: __type(name: "Named") {
                kind
                name
                fields { name }
                interfaces { name }
                possibleTypes { name }
                enumValues { name }
                inputFields { name }
            }
            Pet: __type(name: "Pet") {
                kind
                name
                fields { name }
                interfaces { name }
                possibleTypes { name }
                enumValues { name }
                inputFields { name }
            }
        }
        """,
        executor_cls=executor_cls,
        expected_data={
            "Named": {
                "enumValues": None,
                "fields": [{"name": "name"}],
                "inputFields": None,
                "interfaces": None,
                "kind": "INTERFACE",
                "name": "Named",
                "possibleTypes": [
                    {"name": "Cat"},
                    {"name": "Dog"},
                    {"name": "Person"},
                ],
            },
            "Pet": {
                "enumValues": None,
                "fields": None,
                "inputFields": None,
                "interfaces": None,
                "kind": "UNION",
                "name": "Pet",
                "possibleTypes": [{"name": "Cat"}, {"name": "Dog"}],
            },
        },
    )


async def test_it_executes_union_types(executor_cls):
    # This is an *invalid* query, but it should be an *executable* query.
    await assert_execution(
        _SCHEMA,
        """
        {
            __typename
            name
            pets {
                __typename
                name
                woofs
                meows
            }
        }
        """,
        expected_data={
            "__typename": "Person",
            "name": "John",
            "pets": [
                {"__typename": "Cat", "meows": False, "name": "Garfield"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
        },
        executor_cls=executor_cls,
        initial_value=_JOHN,
    )


async def test_it_executes_union_types_using_inline_fragments(executor_cls):
    # This is the valid version of the query in the above test.
    await assert_execution(
        _SCHEMA,
        """
        {
            __typename
            name
            pets {
                __typename
                ... on Dog { name woofs }
                ... on Cat { name meows }
            }
        }
        """,
        initial_value=_JOHN,
        executor_cls=executor_cls,
        expected_data={
            "__typename": "Person",
            "name": "John",
            "pets": [
                {"__typename": "Cat", "meows": False, "name": "Garfield"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
        },
    )


async def test_it_executes_interface_types(executor_cls):
    # This is an *invalid* query, but it should be an *executable* query.
    await assert_execution(
        _SCHEMA,
        """
        {
            __typename
            name
            friends {
                __typename
                name
                woofs
                meows
            }
        }
        """,
        initial_value=_JOHN,
        executor_cls=executor_cls,
        expected_data={
            "__typename": "Person",
            "friends": [
                {"__typename": "Person", "name": "Liz"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
            "name": "John",
        },
    )


async def test_it_executes_interface_types_using_inline_fragments(executor_cls):
    # This is the valid version of the query in the above test.
    await assert_execution(
        _SCHEMA,
        """
        {
            __typename
            name
            friends {
                __typename
                name
                ... on Dog { woofs }
                ... on Cat { meows }
            }
        }
        """,
        initial_value=_JOHN,
        executor_cls=executor_cls,
        expected_data={
            "__typename": "Person",
            "friends": [
                {"__typename": "Person", "name": "Liz"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
            "name": "John",
        },
    )


async def test_it_allows_fragment_conditions_to_be_abstract_types(executor_cls):
    await assert_execution(
        _SCHEMA,
        """
        {
            __typename
            name
            pets { ...PetFields }
            friends { ...FriendFields }
        }

        fragment PetFields on Pet {
            __typename
            ... on Dog { name woofs }
            ... on Cat { name meows }
        }

        fragment FriendFields on Named {
            __typename
            name
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        """,
        initial_value=_JOHN,
        executor_cls=executor_cls,
        expected_data={
            "__typename": "Person",
            "friends": [
                {"__typename": "Person", "name": "Liz"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
            "name": "John",
            "pets": [
                {"__typename": "Cat", "meows": False, "name": "Garfield"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
        },
    )
