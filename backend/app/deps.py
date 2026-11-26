"""Shared FastAPI dependencies for authentication."""

from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


def get_room_actor(code: str, actor: dict[str, Any] = Depends(get_actor)) -> dict[str, Any]:
    """Resolve the caller for a /rooms/{code} route.

    Guest tokens are bound to the room they were issued for, mirroring the
    websocket check in ws.py: a guest token for another room gets a 403.
    """
    if actor.get("scope") == "guest" and actor.get("room") != code.upper():
        raise forbidden("That guest token belongs to a different room")
    return actor


def get_user_actor(actor: dict[str, Any] = Depends(get_actor)) -> dict[str, Any]:
    if actor.get("scope") != "user":
        raise unauthorized("A host account is required for that action")
    return actor
