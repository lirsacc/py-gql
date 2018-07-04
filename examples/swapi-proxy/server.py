# -*- coding: utf-8 -*-
# fmt: off
""" Simple example GraphQL server translating and proxying the queries to
https://swapi.co using no external dependency.
"""

import os
from flask import Flask, Response, request, jsonify

from py_gql import graphql, ThreadPoolExecutor
from py_gql.schema import print_schema
from py_gql.utilities.tracers import ApolloTracer

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

    tracer = ApolloTracer()

    result = graphql(
        schema,
        data['query'],
        data.get('variables', {}),
        data.get('operation_name'),
        executor=EXECUTOR,
        tracer=tracer,
    )

    result.add_extension(tracer)

    return jsonify(result.response())


@app.route('/graphiql')
def grahiql_route():
    return GRAPHIQL_HTML
