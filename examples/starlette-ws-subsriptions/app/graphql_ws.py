# -*- coding: utf-8 -*-
"""
Very basic implementation of the [GraphQL WS protocol]
(https://github.com/apollographql/subscriptions-transport-ws/blob/master/PROTOCOL.md)
for [Startlette](https://www.starlette.io/).
"""

import asyncio
import enum
import logging
import uuid
from typing import Any, Dict, Optional

from starlette.websockets import WebSocket

from py_gql.exc import ExecutionError, GraphQLResponseError, GraphQLSyntaxError
from py_gql.execution import execute, get_operation, subscribe
from py_gql.execution.runtime import AsyncIORuntime
from py_gql.lang import parse
from py_gql.schema import Schema

logger = logging.getLogger(__name__)


class ClientMessage(enum.Enum):
    CONNECTION_INIT = enum.auto()
    START = enum.auto()
    STOP = enum.auto()
    CONNECTION_TERMINATE = enum.auto()


class ServerMessage(enum.Enum):
    CONNECTION_ERROR = enum.auto()
    CONNECTION_ACK = enum.auto()
    DATA = enum.auto()
    ERROR = enum.auto()
    COMPLETE = enum.auto()
    KA = enum.auto()


class ConnectionStatus(enum.Enum):
    PENDING = enum.auto()
    INITIALIZED = enum.auto()
    TERMINATED = enum.auto()


class GraphQLWSHandler:
    def __init__(
        self,
        ws: WebSocket,
        schema: Schema,
        context: Any = None,
        root: Any = None,
    ):
        self.ws = ws
        self.schema = schema
        self.context = context
        self.root = root
        self.id = uuid.uuid4()

        self.status = ConnectionStatus.PENDING

        self.operations: Dict[str, asyncio.Task[Any]] = {}
        self.keepalive: Optional[asyncio.Task[Any]] = None

        logger.info("[%r] Opened", self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id})"

    async def send(self, msg_type: ServerMessage, **fields: Any) -> None:
        await self.ws.send_json({"type": msg_type.name.lower(), **fields})

    def close(self) -> None:
        if self.status is ConnectionStatus.TERMINATED:
            return

        if self.keepalive:
            self.keepalive.cancel()

        for x in self.operations.values():
            x.cancel()

        self.status = ConnectionStatus.TERMINATED
        logger.info("[%r] Closed", self)

    async def handle_query_or_mutation(
        self, msg_id, document, variables, operation_name
    ):
        async def run():
            try:
                result = await execute(
                    self.schema,
                    document,
                    variables=variables,
                    operation_name=operation_name,
                    context_value=self.context,
                    initial_value=self.root,
                    runtime=AsyncIORuntime(),
                )
            except GraphQLResponseError as err:
                await self.send(
                    ServerMessage.ERROR,
                    id=msg_id,
                    payload={"errors": [err.to_dict()]},
                )
            else:
                await self.send(
                    ServerMessage.DATA, id=msg_id, payload=result.response()
                )
                await self.send(ServerMessage.COMPLETE, id=msg_id)

        self.operations[msg_id] = asyncio.create_task(run())

    async def handle_subscription(
        self, msg_id, document, variables, operation_name
    ):
        async def run():
            try:
                iterator = await subscribe(
                    self.schema,
                    document,
                    variables=variables,
                    operation_name=operation_name,
                    context_value=self.context,
                    initial_value=self.root,
                    runtime=AsyncIORuntime(),
                )
            except GraphQLResponseError as err:
                await self.send(
                    ServerMessage.ERROR,
                    id=msg_id,
                    payload={"errors": [err.to_dict()]},
                )
            else:
                try:
                    async for result in iterator:
                        if msg_id not in self.operations:
                            break

                        await self.send(
                            ServerMessage.DATA,
                            id=msg_id,
                            payload=result.response(),
                        )
                except asyncio.CancelledError:
                    pass
                except Exception as err:
                    logger.error(
                        "Error in subscription %r: %r",
                        msg_id,
                        err,
                        exc_info=True,
                    )
                    raise

        self.operations[msg_id] = asyncio.create_task(run())

    async def initialize(self):
        self.status = ConnectionStatus.INITIALIZED
        await self.send(ServerMessage.CONNECTION_ACK)

        async def keepalive():
            while True:
                await self.send(ServerMessage.KA)
                await asyncio.sleep(1)

        self.keepalive = asyncio.get_event_loop().create_task(keepalive())

    def cancel_operation(self, msg_id):
        logger.info("[%r] Dropping operation %r", self, msg_id)

        try:
            self.operations.pop(msg_id).cancel()
        except KeyError:
            pass

    async def handle(self, ws: WebSocket) -> None:
        while True:
            msg = await ws.receive_json()

            if self.status is ConnectionStatus.TERMINATED:
                await ws.close(code=1000)
                break

            logger.info("[%r] Message = %r", self, msg)

            try:
                msg_type = ClientMessage[msg["type"].upper()]
            except KeyError:
                logger.error("Unknown message type %r.", msg["type"])
                await ws.close(code=1000)
                break

            if self.status is ConnectionStatus.PENDING:
                if msg_type is ClientMessage.CONNECTION_INIT:
                    await self.initialize()
                else:
                    logger.warning(
                        "[%r] Connection has not been initialized yet. "
                        "Ignoring %r message.",
                        self,
                        msg_type,
                    )
            elif msg_type is ClientMessage.STOP:
                self.cancel_operation(msg["id"])

            elif msg_type is ClientMessage.START:

                msg_id = msg["id"]

                try:
                    query = msg["payload"]["query"]
                    operation_name = msg["payload"].get("operation_name", None)
                    variables = msg["payload"].get("variables", None)
                    msg_id = msg["id"]
                except (KeyError, TypeError) as err:
                    await self.send(
                        ServerMessage.CONNECTION_ERROR,
                        id=msg_id,
                        payload={"error": f"Invalid message payload: {err}"},
                    )

                try:
                    document = parse(query)
                    operation = get_operation(document)
                except (GraphQLSyntaxError, ExecutionError) as err:
                    await self.send(
                        ServerMessage.ERROR,
                        id=msg_id,
                        payload={"errors": [err.to_dict()]},
                    )
                else:
                    if operation.operation in ("query", "mutation"):
                        await self.handle_query_or_mutation(
                            msg_id, document, variables, operation_name
                        )
                    else:
                        await self.handle_subscription(
                            msg_id, document, variables, operation_name
                        )
