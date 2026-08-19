"""Live chat WebSocket endpoint for a show.

Anyone may connect and watch the chat; posting requires a valid token (passed as
``?token=``). Messages are persisted and broadcast to the ``chat:<id>`` room.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from ..db import engine as db_engine
from ..models import ChatMessage, Show
from .auction import _user_from_token
from .rooms import rooms

router = APIRouter(tags=["realtime"])

MAX_LEN = 500
HISTORY = 30


@router.websocket("/ws/shows/{show_id}/chat")
async def chat_ws(ws: WebSocket, show_id: int, token: str | None = None):
    await ws.accept()
    room = f"chat:{show_id}"
    with Session(db_engine) as s:
        if s.get(Show, show_id) is None:
            await ws.close(code=4404)
            return
        user = _user_from_token(token, s)
        recent = s.exec(
            select(ChatMessage)
            .where(ChatMessage.show_id == show_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(HISTORY)
        ).all()

    await rooms.join(room, ws)
    # Replay recent history (oldest first) to the newcomer.
    for m in reversed(recent):
        await ws.send_json({
            "type": "message", "username": m.username, "text": m.text,
            "ts": m.created_at.isoformat(),
        })

    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") != "message":
                continue
            if user is None:
                await ws.send_json({"type": "error", "error": "Log in to chat"})
                continue
            text = str(data.get("text", "")).strip()[:MAX_LEN]
            if not text:
                continue
            with Session(db_engine) as s:
                msg = ChatMessage(show_id=show_id, user_id=user.id, username=user.username, text=text)
                s.add(msg)
                s.commit()
                s.refresh(msg)
                payload = {
                    "type": "message", "username": msg.username, "text": msg.text,
                    "ts": msg.created_at.isoformat(),
                }
            await rooms.broadcast(room, payload)
    except WebSocketDisconnect:
        await rooms.leave(room, ws)
    except Exception:
        await rooms.leave(room, ws)
