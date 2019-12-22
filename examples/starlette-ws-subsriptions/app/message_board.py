# -*- coding: utf-8 -*-
"""
Simple database for our message board example.
"""

import datetime
import uuid
from typing import Callable, Dict, List, Set

from mypy_extensions import TypedDict

Message = TypedDict(
    "Message",
    {
        "id": uuid.UUID,
        "created": int,
        "text": str,
        "author": str,
        "room_id": uuid.UUID,
    },
)


Room = TypedDict(
    "Room",
    {"id": uuid.UUID, "created": int, "name": str, "messages": List[uuid.UUID]},
)


Callback = Callable[[Message], None]


class MessageBoard:
    def __init__(self):
        self.rooms: Dict[uuid.UUID, Room] = {}
        self.room_names: Set[str] = set()
        self.messages: Dict[uuid.UUID, Message] = {}
        self.callbacks: Set[Callback] = set()

    def create_room(self, name: str) -> Room:
        if name in self.room_names:
            raise ValueError("Room '{}' already exists.".format(name))

        room_id = uuid.uuid4()

        self.rooms[room_id] = room = Room(
            id=room_id,
            created=int(datetime.datetime.utcnow().timestamp()),
            name=name,
            messages=[],
        )
        self.room_names.add(name)

        return room

    def add_callback(self, cb: Callback) -> None:
        self.callbacks.add(cb)

    def remove_callback(self, cb: Callback) -> None:
        self.callbacks.remove(cb)

    def notify_callbacks(self, msg: Message) -> None:
        for cb in self.callbacks:
            cb(msg)

    def create_message(
        self, room_id: uuid.UUID, text: str, author: str
    ) -> Message:
        try:
            room = self.rooms[room_id]
        except KeyError:
            raise ValueError("Room '{}' doesn't exist.".format(room_id))

        msg_id = uuid.uuid4()
        self.messages[msg_id] = msg = Message(
            id=msg_id,
            created=int(datetime.datetime.utcnow().timestamp()),
            text=text,
            author=author,
            room_id=room_id,
        )
        room["messages"].append(msg_id)
        self.notify_callbacks(msg)
        return msg
