# -*- coding: utf-8 -*-

import os
from concurrent import futures

import flask

from py_gql._graphql import do_graphql
from py_gql.execution.threadpool_executor import ThreadPoolExecutor
from schema import SCHEMA

SCHEMA_SDL = SCHEMA.to_string()
GLOBAL_EXECUTOR = futures.ThreadPoolExecutor(max_workers=20)

with open(os.path.join(os.path.dirname(__file__), "graphiql.html")) as f:
    GRAPHIQL_HTML = f.read()


app = flask.Flask(__name__)


@app.route("/sdl")
def sdl_route():
    return flask.Response(SCHEMA_SDL, mimetype="text")


@app.route("/graphql", methods=("POST",))
def graphql_route():

    data = flask.request.json

    result = do_graphql(
        SCHEMA,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        executor_cls=ThreadPoolExecutor,
        context=dict(global_executor=GLOBAL_EXECUTOR),
        executor_args=dict(inner_executor=GLOBAL_EXECUTOR),
    )

    return flask.jsonify(result.result().response())


@app.route("/graphiql")
def grahiql_route():
    return GRAPHIQL_HTML
