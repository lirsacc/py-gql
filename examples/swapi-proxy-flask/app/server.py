# -*- coding: utf-8 -*-

import os

import flask

from py_gql import process_graphql_query
from py_gql.execution.runtime import ThreadPoolRuntime
from py_gql.schema.transforms import CamelCaseSchemaTransform, transform_schema
from py_gql.tracers import ApolloTracer

from .schema import SCHEMA


RUNTIME = ThreadPoolRuntime(max_workers=20)

with open(os.path.join(os.path.dirname(__file__), "graphiql.html")) as f:
    GRAPHIQL_HTML = f.read()


app = flask.Flask(__name__)

# Let the initial order be respected.
app.config["JSON_SORT_KEYS"] = False

CAMEL_CASED_SCHEMA = transform_schema(SCHEMA, CamelCaseSchemaTransform())
SCHEMA_SDL = CAMEL_CASED_SCHEMA.to_string()


@app.route("/sdl")
def sdl_route():
    return flask.Response(SCHEMA_SDL, mimetype="text")


@app.route("/graphql", methods=("POST",))
def graphql_route():

    data = flask.request.json

    tracer = ApolloTracer()

    result = process_graphql_query(
        CAMEL_CASED_SCHEMA,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        instrumentation=tracer,
        runtime=RUNTIME,
    ).result()

    result.add_extension(tracer)

    return flask.jsonify(result.response())


@app.route("/graphiql")
def grahiql_route():
    return GRAPHIQL_HTML
