# -*- coding: utf-8 -*-
"""
This defines a basic set of data and the Star Wars Schema used for testing
and examples. It describes the major characters in the original
Star Wars trilogy.

NOTE: This may contain spoilers for the original Star Wars trilogy.

NOTE: The data is hard coded for the sake of the demo, but you could imagine
fetching this data from a backend service like SWApi rather than from hardcoded
JSON objects in a more complex demo.
"""

from py_gql.exc import ResolverError
from py_gql.schema import (
    Argument,
    EnumType,
    EnumValue,
    Field,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
)

luke = {
    "type": "Human",
    "id": "1000",
    "name": "Luke Skywalker",
    "friends": ["1002", "1003", "2000", "2001"],
    "appearsIn": [4, 5, 6],
    "homePlanet": "Tatooine",
}

vader = {
    "type": "Human",
    "id": "1001",
    "name": "Darth Vader",
    "friends": ["1004"],
    "appearsIn": [4, 5, 6],
    "homePlanet": "Tatooine",
}

han = {
    "type": "Human",
    "id": "1002",
    "name": "Han Solo",
    "friends": ["1000", "1003", "2001"],
    "appearsIn": [4, 5, 6],
}

leia = {
    "type": "Human",
    "id": "1003",
    "name": "Leia Organa",
    "friends": ["1000", "1002", "2000", "2001"],
    "appearsIn": [4, 5, 6],
    "homePlanet": "Alderaan",
}

tarkin = {
    "type": "Human",
    "id": "1004",
    "name": "Wilhuff Tarkin",
    "friends": ["1001"],
    "appearsIn": [4],
}

human_data = {
    "1000": luke,
    "1001": vader,
    "1002": han,
    "1003": leia,
    "1004": tarkin,
}

threepio = {
    "type": "Droid",
    "id": "2000",
    "name": "C-3PO",
    "friends": ["1000", "1002", "1003", "2001"],
    "appearsIn": [4, 5, 6],
    "primaryFunction": "Protocol",
}

artoo = {
    "type": "Droid",
    "id": "2001",
    "name": "R2-D2",
    "friends": ["1000", "1002", "1003"],
    "appearsIn": [4, 5, 6],
    "primaryFunction": "Astromech",
}

droid_data = {"2000": threepio, "2001": artoo}


def get_character(id_):
    return get_human(id_) or get_droid(id_)


def get_friends(character):
    return [get_character(f) for f in character["friends"]]


def get_hero(episode):
    if episode == 5:
        return luke
    return artoo


def get_human(id_):
    return human_data.get(id_)


def get_droid(id_):
    return droid_data.get(id_)


Episode = EnumType(
    "Episode",
    [
        EnumValue("NEWHOPE", 4, description="Released in 1977."),
        EnumValue("EMPIRE", 5, description="Released in 1980."),
        EnumValue("JEDI", 6, description="Released in 1983."),
    ],
    description="One of the films in the Star Wars Trilogy",
)


def resolve_character_type(character, *_):
    return {"Human": Human, "Droid": Droid}[character["type"]]


Character = InterfaceType(
    "Character",
    [
        Field(
            "id", NonNullType(String), description="The id of the character."
        ),
        Field("name", String, description="The name of the character."),
        Field(
            "friends",
            ListType(lambda: Character),
            description=(
                "The friends of the character, or an empty list if they have "
                "none."
            ),
        ),
        Field(
            "appearsIn",
            ListType(Episode),
            description="Which movies they appear in.",
        ),
        Field(
            "secretBackstory",
            String,
            description="All secrets about their past.",
        ),
    ],
    description="A character in the Star Wars Trilogy",
    resolve_type=resolve_character_type,
)  # type: InterfaceType


def resolve_secret_backstory(*args, **kwargs):
    raise ResolverError("secretBackstory is secret.", extensions={"code": 42})


Human = ObjectType(
    "Human",
    [
        Field("id", NonNullType(String), description="The id of the human."),
        Field("name", String, description="The name of the human."),
        Field(
            "friends",
            ListType(lambda: Character),
            description=(
                "The friends of the human, or an empty list if they have "
                "none."
            ),
            resolver=lambda human, *r, **k: get_friends(human),
        ),
        Field(
            "appearsIn",
            ListType(Episode),
            description="Which movies they appear in.",
        ),
        Field(
            "secretBackstory",
            String,
            description=(
                "Where are they from and how they came to be who they are."
            ),
            resolver=resolve_secret_backstory,
        ),
        Field(
            "homePlanet",
            String,
            description="The home planet of the human, or null if unknown.",
        ),
    ],
    description="A humanoid creature in the Star Wars universe.",
    interfaces=[Character],
)

Droid = ObjectType(
    "Droid",
    [
        Field("id", NonNullType(String), description="The id of the droid."),
        Field("name", String, description="The name of the droid."),
        Field(
            "friends",
            ListType(lambda: Character),
            description=(
                "The friends of the droid, or an empty list if they have "
                "none."
            ),
            resolver=lambda droid, *r, **k: get_friends(droid),
        ),
        Field(
            "appearsIn",
            ListType(Episode),
            description="Which movies they appear in.",
        ),
        Field(
            "secretBackstory",
            String,
            description=(
                "Where are they from and how they came to be who they are."
            ),
            resolver=resolve_secret_backstory,
        ),
        Field(
            "primaryFunction",
            String,
            description="The primary function of the droid.",
        ),
    ],
    description="A mechanical creature in the Star Wars universe.",
    interfaces=[Character],
)


Query = ObjectType(
    "Query",
    [
        Field(
            "hero",
            Character,
            [
                Argument(
                    "episode",
                    Episode,
                    description=(
                        "If omitted, returns the hero of the whole saga. If "
                        "provided, returns the hero of that particular episode."
                    ),
                )
            ],
            resolver=lambda *_, **args: get_hero(args.get("episode")),
        ),
        Field(
            "human",
            Human,
            [
                Argument(
                    "id", NonNullType(String), description="Id of the human"
                )
            ],
            resolver=lambda *_, **args: get_human(args.get("id")),
        ),
        Field(
            "droid",
            Droid,
            [
                Argument(
                    "id", NonNullType(String), description="Id of the droid"
                )
            ],
            resolver=lambda *_, **args: get_droid(args.get("id")),
        ),
    ],
)

StarWarsSchema = Schema(Query, types=[Human, Droid])
