"""In-process room registry for WebSocket fan-out.

A "room" is a string key (e.g. ``chat:42`` or ``auction:42``). Each room holds a
set of connected WebSockets; :meth:`broadcast` sends a JSON payload to all of
them and prunes any that have dropped. Single-process only — swap for Redis
pub/sub to scale across workers (see docs/ARCHITECTURE.md).
"""
from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].add(ws)

    async def leave(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms.get(room, set()).discard(ws)
            if room in self._rooms and not self._rooms[room]:
                del self._rooms[room]

    def count(self, room: str) -> int:
        return len(self._rooms.get(room, ()))

    async def broadcast(self, room: str, payload: dict) -> None:
        # Snapshot to avoid mutation during iteration.
        conns = list(self._rooms.get(room, ()))
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms.get(room, set()).discard(ws)


rooms = RoomManager()
