# -*- coding: utf-8 -*-

import json
import os

from aiohttp import web

from py_gql.asyncio import AsyncIOExecutor, graphql
from py_gql.utilities.tracers import ApolloTracer
from schema import schema

SCHEMA_SDL = schema.to_string()

with open(os.path.join(os.path.dirname(__file__), "graphiql.html")) as f:
    GRAPHIQL_HTML = f.read()


async def sdl(request):
    return web.Response(text=SCHEMA_SDL, content_type="text")


async def graphql_handler(request):
    data = await request.json()

    tracer = ApolloTracer()

    with AsyncIOExecutor() as executor:
        result = await graphql(
            schema,
            data["query"],
            data.get("variables", {}),
            data.get("operation_name"),
            executor=executor,
            tracer=tracer,
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
