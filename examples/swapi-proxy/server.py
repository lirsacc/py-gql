# -*- coding: utf-8 -*-

import os

from flask import Flask, Response, jsonify, request
from py_gql import ThreadPoolExecutor, graphql
from py_gql.utilities.tracers import ApolloTracer
from schema import schema

SCHEMA_SDL = schema.to_string()
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
