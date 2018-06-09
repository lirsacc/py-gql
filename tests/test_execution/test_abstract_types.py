# -*- coding: utf-8 -*-
""" execution tests related to abstract types (Interface, Union) """
from __future__ import unicode_literals

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

from ._test_utils import check_execution


class Dog(object):
    def __init__(self, name, woofs):
        self.name = name
        self.woofs = woofs


class Cat(object):
    def __init__(self, name, meows):
        self.name = name
        self.meows = meows


class Human(object):
    def __init__(self, name):
        self.name = name


class Person(object):
    def __init__(self, name, pets, friends):
        self.name = name
        self.pets = pets
        self.friends = friends


def test_ObjectType_is_type_of_for_interface_runtime_inference():
    PetType = InterfaceType("Pet", [Field("name", String)])

    DogType = ObjectType(
        "Dog",
        [Field("name", String), Field("woofs", Boolean)],
        interfaces=[PetType],
        is_type_of=Dog,
    )

    CatType = ObjectType(
        "Cat",
        [Field("name", String), Field("meows", Boolean)],
        interfaces=[PetType],
        is_type_of=Cat,
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolve=lambda *_: [Dog("Odie", True), Cat("Garfield", False)],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    check_execution(
        schema,
        """{
            pets {
                name
                __typename
                ... on Dog { woofs }
                ... on Cat { meows }
            }
        }""",
        expected_data={
            "pets": [
                {"name": "Odie", "woofs": True, "__typename": "Dog"},
                {"name": "Garfield", "meows": False, "__typename": "Cat"},
            ]
        },
        expected_errors=[],
    )


def test_ObjectType_is_type_of_for_union_runtime_inference():
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
                    resolve=lambda *_: [Dog("Odie", True), Cat("Garfield", False)],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    check_execution(
        schema,
        """{
            pets {
                __typename
                ... on Dog { woofs, name }
                ... on Cat { meows, name }
            }
        }""",
        expected_data={
            "pets": [
                {"name": "Odie", "woofs": True, "__typename": "Dog"},
                {"name": "Garfield", "meows": False, "__typename": "Cat"},
            ]
        },
        expected_errors=[],
    )


def test_type_resolution_on_interface_yields_useful_error():
    """ Different from ref implementation -> this should never happen
    so we crash """

    def _resolve_pet_type(value, **_):
        return {Dog: DogType, Cat: CatType, Human: HumanType}.get(type(value), None)

    PetType = InterfaceType(
        "Pet", [Field("name", String)], resolve_type=_resolve_pet_type
    )

    HumanType = ObjectType("Human", [Field("name", String)])

    DogType = ObjectType(
        "Dog", [Field("name", String), Field("woofs", Boolean)], interfaces=[PetType]
    )

    CatType = ObjectType(
        "Cat", [Field("name", String), Field("meows", Boolean)], interfaces=[PetType]
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolve=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                        Human("Jon"),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    check_execution(
        schema,
        """{
        pets {
            name
            __typename
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        }""",
        expected_exc=RuntimeError,
        expected_msg=(
            'Runtime ObjectType "Human" is not a possible type for field '
            '"pets[2]" of type "Pet".'
        ),
    )


def test_type_resolution_on_union_yields_useful_error():
    """ Different from ref implementation -> this should never happen
    so we crash """

    def _resolve_pet_type(value, **_):
        return {Dog: DogType, Cat: CatType, Human: HumanType}.get(type(value), None)

    PetType = InterfaceType(
        "Pet", [Field("name", String)], resolve_type=_resolve_pet_type
    )

    HumanType = ObjectType("Human", [Field("name", String)])

    DogType = ObjectType("Dog", [Field("name", String), Field("woofs", Boolean)])

    CatType = ObjectType("Cat", [Field("name", String), Field("meows", Boolean)])

    PetType = UnionType("Pet", [DogType, CatType], resolve_type=_resolve_pet_type)

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolve=lambda *_: [
                        Dog("Odie", True),
                        Cat("Garfield", False),
                        Human("Jon"),
                    ],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    check_execution(
        schema,
        """{
        pets {
            __typename
            ... on Dog { woofs, name }
            ... on Cat { meows, name }
        }
        }""",
        expected_exc=RuntimeError,
        expected_msg=(
            'Runtime ObjectType "Human" is not a possible type for field '
            '"pets[2]" of type "Pet".'
        ),
    )


def test_type_resolution_supports_strings():
    def _resolve_pet_type(value, **_):
        return type(value).__name__

    PetType = InterfaceType(
        "Pet", [Field("name", String)], resolve_type=_resolve_pet_type
    )

    DogType = ObjectType(
        "Dog", [Field("name", String), Field("woofs", Boolean)], interfaces=[PetType]
    )

    CatType = ObjectType(
        "Cat", [Field("name", String), Field("meows", Boolean)], interfaces=[PetType]
    )

    schema = Schema(
        ObjectType(
            "Query",
            [
                Field(
                    "pets",
                    ListType(PetType),
                    resolve=lambda *_: [Dog("Odie", True), Cat("Garfield", False)],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    check_execution(
        schema,
        """{
        pets {
            name
            __typename
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        }""",
        expected_errors=[],
    )


def test_type_resolution_supports_object_attribute():
    PetType = InterfaceType("Pet", [Field("name", String)])

    DogType = ObjectType(
        "Dog", [Field("name", String), Field("woofs", Boolean)], interfaces=[PetType]
    )

    CatType = ObjectType(
        "Cat", [Field("name", String), Field("meows", Boolean)], interfaces=[PetType]
    )

    class Dog(object):
        __graphql_type__ = DogType

        def __init__(self, name, woofs):
            self.name = name
            self.woofs = woofs

    class Cat(object):
        __graphql_type__ = "Cat"

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
                    resolve=lambda *_: [Dog("Odie", True), Cat("Garfield", False)],
                )
            ],
        ),
        types=[DogType, CatType],
    )

    check_execution(
        schema,
        """{
        pets {
            name
            __typename
            ... on Dog { woofs }
            ... on Cat { meows }
        }
        }""",
        expected_errors=[],
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


def _resolve_pet_type(value, *a, **kw):
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


def test_it_can_introspect_on_union_and_intersection_types():
    check_execution(
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
        {
            "Named": {
                "enumValues": None,
                "fields": [{"name": "name"}],
                "inputFields": None,
                "interfaces": None,
                "kind": "INTERFACE",
                "name": "Named",
                "possibleTypes": [{"name": "Cat"}, {"name": "Dog"}, {"name": "Person"}],
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
        [],
    )


def test_it_executes_union_types():
    # This is an *invalid* query, but it should be an *executable* query.
    check_execution(
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
        {
            "__typename": "Person",
            "name": "John",
            "pets": [
                {"__typename": "Cat", "meows": False, "name": "Garfield"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
        },
        [],
        initial_value=_JOHN,
    )


def test_it_executes_union_types_using_inline_fragments():
    # This is the valid version of the query in the above test.
    check_execution(
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
        {
            "__typename": "Person",
            "name": "John",
            "pets": [
                {"__typename": "Cat", "meows": False, "name": "Garfield"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
        },
        [],
        initial_value=_JOHN,
    )


def test_it_executes_interface_types():
    # This is an *invalid* query, but it should be an *executable* query.
    check_execution(
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
        {
            "__typename": "Person",
            "friends": [
                {"__typename": "Person", "name": "Liz"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
            "name": "John",
        },
        [],
        initial_value=_JOHN,
    )


def test_it_executes_interface_types_using_inline_fragments():
    # This is the valid version of the query in the above test.
    check_execution(
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
        {
            "__typename": "Person",
            "friends": [
                {"__typename": "Person", "name": "Liz"},
                {"__typename": "Dog", "name": "Odie", "woofs": True},
            ],
            "name": "John",
        },
        [],
        initial_value=_JOHN,
    )


def test_it_allows_fragment_conditions_to_be_abstract_types():
    check_execution(
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
        {
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
        [],
        initial_value=_JOHN,
    )
