# -*- coding: utf-8 -*-

import json
import os

from aiohttp import web

from py_gql import graphql
from py_gql.tracers import ApolloTracer
from schema import SCHEMA

SCHEMA_SDL = SCHEMA.to_string()

with open(os.path.join(os.path.dirname(__file__), "graphiql.html")) as f:
    GRAPHIQL_HTML = f.read()


async def sdl(request):
    return web.Response(text=SCHEMA_SDL, content_type="text")


async def graphql_handler(request):
    data = await request.json()

    tracer = ApolloTracer()

    result = await graphql(
        SCHEMA,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        instrumentation=tracer,
    )

    result.add_extension(tracer)

    return web.Response(
        text=json.dumps(result.response()), content_type="application/json"
    )


async def graphiql(request):
    return web.Response(text=GRAPHIQL_HTML, content_type="text/html")


def init(argv=None):
    app = web.Application()
    app.add_routes(
        [
            web.get("/sdl", sdl),
            web.get("/graphiql", graphiql),
            web.post("/graphql", graphql_handler),
        ]
    )
    return app
