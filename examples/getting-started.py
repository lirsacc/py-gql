# -*- coding: utf-8 -*-
""" Minimal getting started example with Flask.

To run this, make sure Flask and py_gql are installed and run:

    FLASK_APP=getting-started.py flask run
"""

import json

import flask

from py_gql import build_schema, graphql_blocking

SDL = """
enum CharacterType {
    Human,
    Droid,
}

type Query {
    hero: Person!,
    characters: [Person]!,
    character(id: Int!): Person,
}

type Person {
    id: Int!,
    name: String,
    type: CharacterType,
}
"""

DATA = """
[
  {
    "type": "Droid",
    "id": 2000,
    "name": "C-3PO"
  },
  {
    "type": "Droid",
    "id": 2001,
    "name": "R2-D2"
  },
  {
    "type": "Human",
    "id": 1000,
    "name": "Luke Skywalker"
  },
  {
    "type": "Human",
    "id": 1001,
    "name": "Darth Vader"
  },
  {
    "type": "Human",
    "id": 1002,
    "name": "Han Solo"
  },
  {
    "type": "Human",
    "id": 1003,
    "name": "Leia Organa"
  },
  {
    "type": "Human",
    "id": 1004,
    "name": "Wilhuff Tarkin"
  }
]
"""

schema = build_schema(SDL)
database = {row["id"]: row for row in json.loads(DATA)}


@schema.resolver("Query.hero")
def resolve_hero(_root, ctx, _info):
    return ctx["db"][2000]  # R2-D2


@schema.resolver("Query.characters")
def resolve_characters(_root, ctx, _info):
    return ctx["db"].items()


@schema.resolver("Query.character")
def resolve_character(_root, ctx, _info, *, id):
    return ctx["db"].get(id, None)


app = flask.Flask(__name__)


@app.route("/graphql", methods=("POST",))
def graphql_route():
    data = flask.request.json

    result = graphql_blocking(
        schema,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        context=dict(db=database),
    )

    return flask.jsonify(result.response())
