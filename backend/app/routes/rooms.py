"""Room, story and voting routes."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import repositories, schemas, services
from app.config import get_settings
from app.database import get_db
from app.deps import get_room_actor, get_user_actor
from app.rate_limit import limiter
from app.security import create_guest_token

router = APIRouter(prefix="/rooms", tags=["rooms"])


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_mutation_limit(request: Request, code: str) -> None:
    """Rate limit the REST room mutation routes (SEC2).

    Every mutation also triggers a full room broadcast, so an unlimited
    REST surface lets one cheap token generate unbounded database work and
    fan-out. The shipped frontend does in-room actions over the websocket;
    these routes share the existing limiter and window style.
    """
    limiter.check(
        f"room-mutation:{_client_key(request)}:{code.upper()}",
        get_settings().room_mutation_rate_limit,
    )


@router.post("", status_code=201)
async def create_room(
    payload: schemas.CreateRoomRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(get_user_actor),
) -> dict[str, Any]:
    limiter.check(f"rooms:{_client_key(request)}", get_settings().room_rate_limit)
    room = await asyncio.to_thread(repositories.create_room, db, payload.name, str(actor["sub"]))
    state = await services.broadcast_state(db, room)
    return {"room": state["room"], "state": state}


@router.post("/join")
async def join_room(
    payload: schemas.JoinRoomRequest, request: Request, db: Session = Depends(get_db)
) -> dict[str, Any]:
    limiter.check(f"join:{_client_key(request)}", get_settings().auth_rate_limit)
    room = await asyncio.to_thread(services.require_room, db, payload.code)
    token = create_guest_token(room.code, payload.name)
    state = await services.build_state(db, room)
    return {"access_token": token, "room": state["room"], "state": state}


@router.get("/{code}")
async def get_room(
    code: str, db: Session = Depends(get_db), actor: dict[str, Any] = Depends(get_room_actor)
) -> dict[str, Any]:
    room = await asyncio.to_thread(services.require_room, db, code)
    return await services.build_state(db, room)


@router.post("/{code}/stories", status_code=201)
async def add_story(
    code: str,
    payload: schemas.CreateStoryRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(get_room_actor),
) -> dict[str, Any]:
    _check_mutation_limit(request, code)
    room = await asyncio.to_thread(services.require_room, db, code)
    await asyncio.to_thread(services.add_story, db, room, actor, payload.title)
    return await services.broadcast_state(db, room)


@router.post("/{code}/stories/{story_id}/activate")
async def activate_story(
    code: str,
    story_id: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(get_room_actor),
) -> dict[str, Any]:
    _check_mutation_limit(request, code)
    room = await asyncio.to_thread(services.require_room, db, code)
    await asyncio.to_thread(services.activate_story, db, room, actor, story_id)
    return await services.broadcast_state(db, room)


@router.post("/{code}/vote")
async def vote(
    code: str,
    payload: schemas.VoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(get_room_actor),
) -> dict[str, Any]:
    _check_mutation_limit(request, code)
    room = await asyncio.to_thread(services.require_room, db, code)
    await asyncio.to_thread(services.cast_vote, db, room, actor, payload.value)
    return await services.broadcast_state(db, room)


@router.post("/{code}/reveal")
async def reveal(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(get_room_actor),
) -> dict[str, Any]:
    _check_mutation_limit(request, code)
    room = await asyncio.to_thread(services.require_room, db, code)
    await asyncio.to_thread(services.reveal_votes, db, room, actor)
    return await services.broadcast_state(db, room)


@router.post("/{code}/reset")
async def reset(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(get_room_actor),
) -> dict[str, Any]:
    _check_mutation_limit(request, code)
    room = await asyncio.to_thread(services.require_room, db, code)
    await asyncio.to_thread(services.reset_round, db, room, actor)
    return await services.broadcast_state(db, room)
