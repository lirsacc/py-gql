# -*- coding: utf-8 -*-

import asyncio
import uuid
from typing import Any, List, Optional

from mypy_extensions import TypedDict

from py_gql import build_schema
from py_gql.exc import ResolverError
from py_gql.exts.scalars import UUID

from .message_board import Message, MessageBoard, Room


CreateRoomInput = TypedDict("CreateRoomInput", {"name": str})

CreateMessageInput = TypedDict(
    "CreateMessageInput", {"text": str, "author": str}
)

NewMessageEvent = TypedDict("NewMessageEvent", {"new_message": Message})


SDL = """
type Room {
    id: UUID!,
    created: Int!,
    name: String!,
    messages(since: Int, limit: Int): [Message!]!
}

type Message {
    id: UUID!,
    created: Int!,
    text: String!,
    author: String!,
    room: Room!,
}

input CreateRoomInput {
    name: String!,
}

input CreateMessageInput {
    text: String!,
    author: String!,
}

type Query {
    message(id: UUID!): Message,
    room(id: UUID!): Room,
    rooms: [Room]!,
}

type Mutation {
    create_room(data: CreateRoomInput!): Room,
    create_message(room_id: UUID!, data: CreateMessageInput!): Message,
}

type Subscription {
    new_message(room_id: UUID!): Message
}
"""

schema = build_schema(SDL, additional_types=[UUID])


@schema.resolver("Query.rooms")
def resolve_rooms(_root: Any, board: MessageBoard, _info: Any) -> List[Room]:
    return list(board.rooms.values())


@schema.resolver("Room.messages")
def resolve_room_messages(
    room: Room,
    board: MessageBoard,
    _info: Any,
    *,
    since: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[Message]:
    msgs = [board.messages[uid] for uid in room["messages"]]
    msgs = (
        [m for m in msgs if m["created"] > since] if since is not None else msgs
    )
    return msgs[:limit] if limit is not None else msgs


@schema.resolver("Query.message")
def resolve_message(
    _root: Any, board: MessageBoard, _info: Any, *, id: uuid.UUID
) -> Message:
    try:
        return board.messages[id]
    except KeyError:
        raise ResolverError(f"No message with id {id}")


@schema.resolver("Query.room")
def resolve_room(
    _root: Any, board: MessageBoard, _info: Any, *, id: uuid.UUID
) -> Room:
    try:
        return board.rooms[id]
    except KeyError:
        raise ResolverError("No room with id {}".format(id))


@schema.resolver("Mutation.create_room")
def resolve_create_room(
    _root: Any, board: MessageBoard, _info: Any, *, data: CreateRoomInput
) -> Room:
    try:
        return board.create_room(data["name"])
    except ValueError as err:
        raise ResolverError(str(err))


@schema.resolver("Mutation.create_message")
def resolve_create_message(
    _root: Any,
    board: MessageBoard,
    _info: Any,
    *,
    data: CreateMessageInput,
    room_id: uuid.UUID,
) -> Message:
    try:
        return board.create_message(room_id, **data)
    except ValueError as err:
        raise ResolverError(str(err))


@schema.resolver("Message.room")
def resolve_message_room(msg: Message, board: MessageBoard, _info: Any) -> Room:
    return board.rooms[msg["room_id"]]


class NewMessageIterator:
    def __init__(self, loop: asyncio.AbstractEventLoop, room_id: uuid.UUID):
        self.queue: asyncio.Queue[Message] = asyncio.Queue()
        self.room_id = room_id
        self.loop = loop

    def __aiter__(self):
        return self

    async def __anext__(self) -> NewMessageEvent:
        next_msg = await self.queue.get()
        return {"new_message": next_msg}

    def on_message(self, msg: Message) -> None:
        if msg["room_id"] == self.room_id:
            self.loop.call_soon(self.queue.put_nowait, msg)


@schema.subscription("Subscription.new_message")
async def create_messages_subscription(
    _root: Any, board: MessageBoard, _info: Any, room_id: uuid.UUID
) -> NewMessageIterator:

    try:
        board.rooms[room_id]
    except KeyError:
        raise ResolverError("No room with id {}".format(room_id))

    iterator = NewMessageIterator(asyncio.get_event_loop(), room_id)
    board.add_callback(iterator.on_message)
    return iterator
