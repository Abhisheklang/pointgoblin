"""Shared FastAPI dependencies for authentication."""

from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import repositories, services
from app.database import get_db
from app.errors import forbidden, unauthorized
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    """Resolve the caller from a bearer token, or raise 401.

    Header only: tokens in URL query strings leak into access logs, proxy
    logs and browser history, and no shipped client uses them.
    """
    token = credentials.credentials if credentials else ""
    if not token:
        raise unauthorized()
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise unauthorized("That sign in token is not valid") from None
    return payload


def get_optional_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any] | None:
    """Resolve the caller when a token is present, else None.

    Used by routes that work anonymously but behave differently for a
    signed in caller (joining a room records membership, SEC6). A present
    but invalid token is treated as no token.
    """
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except jwt.PyJWTError:
        return None


def get_room_actor(
    code: str,
    actor: dict[str, Any] = Depends(get_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Resolve the caller for a /rooms/{code} route.

    Guest tokens are bound to the room they were issued for, mirroring the
    websocket check in ws.py: a guest token for another room gets a 403.
    User tokens are not room bound, so they need a membership record for
    the room (SEC6): the host qualifies, as does an account that joined
    the room while signed in. A room that does not exist falls through so
    the route raises its usual 404.
    """
    if actor.get("scope") == "guest" and actor.get("room") != code.upper():
        raise forbidden("That guest token belongs to a different room")
    if actor.get("scope") == "user":
        room = repositories.get_room_by_code(db, code)
        if room is not None and not services.is_room_member(db, room, actor):
            raise forbidden("Join this room before reading or voting in it")
    return actor


def get_user_actor(actor: dict[str, Any] = Depends(get_actor)) -> dict[str, Any]:
    if actor.get("scope") != "user":
        raise unauthorized("A host account is required for that action")
    return actor
