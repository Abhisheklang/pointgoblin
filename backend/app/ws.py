"""WebSocket endpoint that streams live room state to participants."""

import asyncio
import json
import logging
import time
from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app import schemas, services
from app.config import get_settings
from app.database import SessionLocal
from app.errors import AppError
from app.events import bus, display_id
from app.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

BROADCAST_COALESCE_SECONDS = 0.075
_pending_broadcasts: dict[str, asyncio.Task[None]] = {}
_dirty_broadcasts: set[str] = set()


class MessageRateLimiter:
    """Fixed window counter for one websocket connection.

    Mirrors the window style of app.rate_limit.RateLimiter, but scoped to a
    single connection so it needs no shared store.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: list[float] = []

    def allow(self) -> bool:
        now = time.monotonic()
        self._hits = [t for t in self._hits if now - t < self._window]
        if len(self._hits) >= self._limit:
            return False
        self._hits.append(now)
        return True


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
    ws_settings = get_settings()

    # Room size cap (K4): refuse a new participant once the room is full.
    people = await bus.get_presence(room_code)
    if len(people) >= ws_settings.max_participants_per_room and all(
        person["id"] != display_id(key) for person in people
    ):
        await websocket.close(code=4413)
        return

    subscription = None
    forward_task: asyncio.Task[None] | None = None
    presence_task: asyncio.Task[None] | None = None
    presence_set = False
    try:
        # Every setup step runs inside the try whose finally removes the
        # presence entry and the subscription, so a failure after
        # set_presence cannot leak a ghost participant (K2).
        await bus.set_presence(room_code, key, str(actor["name"]), is_host)
        presence_set = True
        await websocket.send_json(
            {
                "type": "you",
                "id": display_id(key),
                "name": str(actor["name"]),
                "is_host": is_host,
            }
        )
        subscription = await bus.subscribe(f"room:{room_code}")
        await broadcast_fresh_state(room_code)

        async def forward_events() -> None:
            while True:
                message = await subscription.queue.get()
                try:
                    await asyncio.wait_for(
                        websocket.send_text(message),
                        timeout=ws_settings.ws_send_timeout_seconds,
                    )
                except TimeoutError:
                    # The client stopped reading. Close the socket instead of
                    # buffering state for it forever; the bounded subscription
                    # queue caps what accumulates in the meantime.
                    logger.warning("Closing a websocket whose client stopped reading")
                    try:
                        await asyncio.wait_for(
                            websocket.close(), timeout=ws_settings.ws_send_timeout_seconds
                        )
                    except Exception:
                        pass
                    return

        forward_task = asyncio.create_task(forward_events())

        async def refresh_presence() -> None:
            # Presence entries expire at presence_ttl_seconds so a crashed
            # session does not linger as a ghost (wave 2). A live connection
            # has to refresh its own entry well before that deadline, or it
            # vanishes from the participant list while still connected and
            # able to vote (PG-A1). Only this connection refreshes its own
            # key, so a disconnected participant still expires on schedule.
            interval = max(0.5, ws_settings.presence_ttl_seconds / 3)
            while True:
                await asyncio.sleep(interval)
                await bus.set_presence(room_code, key, str(actor["name"]), is_host)

        presence_task = asyncio.create_task(refresh_presence())
        message_limiter = MessageRateLimiter(
            ws_settings.ws_message_rate_limit, ws_settings.rate_window_seconds
        )
        try:
            while True:
                # Read raw messages and dispatch on type: receive_text()
                # raises KeyError on a binary frame and kills the
                # connection (PG-A2). Binary frames carry no action, so
                # they are ignored and the connection survives.
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    raise WebSocketDisconnect(message.get("code", 1000))
                if message["type"] != "websocket.receive" or "text" not in message:
                    continue
                raw = message["text"]
                # Any activity from a live connection also refreshes its
                # presence entry, on top of the heartbeat above.
                await bus.set_presence(room_code, key, str(actor["name"]), is_host)
                if len(raw.encode("utf-8")) > ws_settings.ws_max_message_bytes:
                    logger.warning("Dropped an oversized websocket message")
                    continue
                if not message_limiter.allow():
                    logger.warning("Dropped a websocket message over the rate limit")
                    continue
                try:
                    await handle_message(websocket, room_code, actor, raw)
                except Exception:
                    logger.exception("Failed to handle a websocket message")
        except WebSocketDisconnect:
            pass
    finally:
        if presence_task is not None:
            presence_task.cancel()
        if forward_task is not None:
            forward_task.cancel()
        if subscription is not None:
            await bus.unsubscribe(subscription)
        if presence_set:
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


def apply_action(room_code: str, actor: dict[str, Any], data: dict[str, Any]) -> str | None:
    """Apply one client action in a worker thread.

    Returns None on success, or the refusal message on failure, so the
    caller can send the client an error frame instead of failing in
    silence (V3).
    """
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
            # Same schema validation as the REST route (V2): blank titles
            # are rejected and over-long titles are refused, never silently
            # truncated.
            try:
                payload = schemas.CreateStoryRequest(title=str(data.get("title", "")))
            except ValidationError:
                return "Story title must be between 1 and 200 characters"
            services.add_story(db, room, actor, payload.title)
        elif action == "activate_story":
            services.activate_story(db, room, actor, str(data.get("story_id", "")))
        else:
            return "Unknown action"
        return None
    except AppError as exc:
        logger.info("Action refused: %s", exc.message)
        return exc.message
    finally:
        db.close()


async def handle_message(
    websocket: WebSocket, room_code: str, actor: dict[str, Any], raw: str
) -> None:
    """Apply one client action, then broadcast the fresh room state.

    Refused actions get an error frame back to the sender (V3), so a
    refused vote, reveal or activation is never invisible to the client.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json(
            {"type": "error", "code": "bad_message", "message": "That message was not valid JSON"}
        )
        return
    if not isinstance(data, dict):
        await websocket.send_json(
            {"type": "error", "code": "bad_message", "message": "That message was not an action"}
        )
        return
    refusal = await asyncio.to_thread(apply_action, room_code, actor, data)
    if refusal is None:
        await broadcast_fresh_state(room_code)
    else:
        await websocket.send_json({"type": "error", "code": "action_refused", "message": refusal})
