"""WebSocket endpoint that streams live room state to participants."""

import asyncio
import json
import logging
from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import services
from app.database import SessionLocal
from app.errors import AppError
from app.events import bus
from app.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

BROADCAST_COALESCE_SECONDS = 0.075
_pending_broadcasts: dict[str, asyncio.Task[None]] = {}
_dirty_broadcasts: set[str] = set()


def authenticate(token: str) -> dict[str, Any] | None:
    try:
        return decode_token(token)
    except jwt.PyJWTError:
        return None


@router.websocket("/ws/rooms/{code}")
async def room_socket(websocket: WebSocket, code: str, token: str = "") -> None:
    actor = authenticate(token)
    if actor is None:
        await websocket.close(code=4401)
        return
    if actor.get("scope") == "guest" and actor.get("room") != code.upper():
        await websocket.close(code=4403)
        return
    await websocket.accept()
    db = SessionLocal()
    try:
        room = services.require_room(db, code)
        room_code = room.code
        host_id = room.host_id
    except AppError:
        await websocket.close(code=4404)
        db.close()
        return
    finally:
        db.close()

    key = services.participant_key(actor)
    is_host = actor.get("scope") == "user" and host_id == actor.get("sub")
    await bus.set_presence(room_code, key, str(actor["name"]), is_host)
    await websocket.send_json({"type": "you", "name": str(actor["name"]), "is_host": is_host})
    subscription = await bus.subscribe(f"room:{room_code}")
    await broadcast_fresh_state(room_code)

    async def forward_events() -> None:
        while True:
            message = await subscription.queue.get()
            await websocket.send_text(message)

    forward_task = asyncio.create_task(forward_events())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                await handle_message(room_code, actor, raw)
            except Exception:
                logger.exception("Failed to handle a websocket message")
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        await bus.unsubscribe(subscription)
        await bus.remove_presence(room_code, key)
        await broadcast_fresh_state(room_code)


def collect_state_data(room_code: str) -> dict[str, Any] | None:
    """Collect the database part of the room state. Runs in a thread."""
    db = SessionLocal()
    try:
        room = services.require_room(db, room_code)
        return services.collect_room_data(db, room)
    except AppError:
        return None
    finally:
        db.close()


async def broadcast_fresh_state(room_code: str) -> None:
    """Broadcast the current room state, coalescing bursts into one send.

    Joins, leaves and votes often arrive in a burst. Sending the full state
    for every single trigger floods every client, so triggers inside a short
    window collapse into one broadcast of the latest state.
    """
    if room_code in _pending_broadcasts:
        _dirty_broadcasts.add(room_code)
        return

    async def send_latest() -> None:
        try:
            await asyncio.sleep(BROADCAST_COALESCE_SECONDS)
            data = await asyncio.to_thread(collect_state_data, room_code)
            if data is not None:
                people = await bus.get_presence(room_code)
                await bus.publish(f"room:{room_code}", services.assemble_state(data, people))
        finally:
            _pending_broadcasts.pop(room_code, None)
            if room_code in _dirty_broadcasts:
                _dirty_broadcasts.discard(room_code)
                await broadcast_fresh_state(room_code)

    _pending_broadcasts[room_code] = asyncio.create_task(send_latest())


def apply_action(room_code: str, actor: dict[str, Any], data: dict[str, Any]) -> bool:
    """Apply one client action in a worker thread. Returns True on success."""
    db = SessionLocal()
    try:
        room = services.require_room(db, room_code)
        action = data.get("action")
        if action == "vote":
            services.cast_vote(db, room, actor, str(data.get("value", "")))
        elif action == "reveal":
            services.reveal_votes(db, room, actor)
        elif action == "reset":
            services.reset_round(db, room, actor)
        elif action == "add_story":
            services.add_story(db, room, actor, str(data.get("title", "")).strip()[:200])
        elif action == "activate_story":
            services.activate_story(db, room, actor, str(data.get("story_id", "")))
        else:
            return False
        return True
    except AppError as exc:
        logger.info("Action refused: %s", exc.message)
        return False
    finally:
        db.close()


async def handle_message(room_code: str, actor: dict[str, Any], raw: str) -> None:
    """Apply one client action, then broadcast the fresh room state."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return
    applied = await asyncio.to_thread(apply_action, room_code, actor, data)
    if applied:
        await broadcast_fresh_state(room_code)
