# -*- coding: utf-8 -*-

import logging
import os
import pickle

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from py_gql import graphql

from .graphql_ws import GraphQLWSHandler
from .message_board import MessageBoard
from .schema import SDL, schema


logger = logging.getLogger(__name__)

PLAYGROUND_FILEPATH = os.path.join(
    os.path.dirname(__file__),
    "./playground.html",
)

DB_FILE = "./db.pickle"

app = Starlette(debug=True)


@app.on_event("startup")
def on_startup():
    with open(PLAYGROUND_FILEPATH) as f:
        app.state.playground_html = f.read()

    try:
        with open(DB_FILE, "rb") as db_f:
            app.state.message_board = pickle.loads(db_f.read())
            logger.info("Used existing database")
    except Exception:
        logger.info("Creating fresh database")
        app.state.message_board = MessageBoard()
        app.state.message_board.create_room("Test")


@app.on_event("shutdown")
def on_shutdown():
    with open(DB_FILE, "wb") as db_f:
        db_f.write(pickle.dumps(app.state.message_board))

    logger.info("Saved database")


@app.route("/sdl")
async def sdl_route(request: Request) -> PlainTextResponse:
    return PlainTextResponse(SDL)


@app.route("/playground")
async def graphiql_route(request: Request) -> HTMLResponse:
    return HTMLResponse(app.state.playground_html)


@app.route("/graphql", methods=("POST",))
async def graphql_route(request: Request) -> JSONResponse:
    data = await request.json()
    execution_result = await graphql(
        schema,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        context=app.state.message_board,
    )
    return JSONResponse(execution_result.response())


@app.websocket_route("/graphql/ws")
async def ws_graphql_route(ws: WebSocket) -> None:

    await ws.accept(subprotocol="graphql-ws")

    handler = GraphQLWSHandler(ws, schema, context=app.state.message_board)

    try:
        await handler.handle(ws)
    except WebSocketDisconnect:
        logger.info("Disconnected")
        handler.close()
    except Exception:
        logger.error(
            "Error when handling GraphqQL over websocket",
            exc_info=True,
        )
