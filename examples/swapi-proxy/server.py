# -*- coding: utf-8 -*-
# fmt: off
""" Simple example GraphQL server translating and proxying the queries to
https://swapi.co using no external dependency.
"""

import os
from flask import Flask, Response, request, jsonify

from py_gql import graphql
from py_gql.schema import print_schema
from py_gql.execution.executors import ThreadPoolExecutor

from schema import schema

SCHEMA_SDL = print_schema(schema)
EXECUTOR = ThreadPoolExecutor(max_workers=20)

with open(os.path.join(os.path.dirname(__file__), "graphiql.html")) as f:
    GRAPHIQL_HTML = f.read()


app = Flask(__name__)


@app.route('/sdl')
def sdl_route():
    return Response(SCHEMA_SDL, mimetype='text')


@app.route('/graphql', methods=('POST',))
def graphql_route():
    data = request.json
    return jsonify(graphql(
        schema,
        data['query'],
        data.get('variables', {}),
        data.get('operation_name'),
        executor=EXECUTOR
    ).response())


@app.route('/graphiql')
def grahiql_route():
    return GRAPHIQL_HTML
