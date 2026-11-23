"""Shared FastAPI dependencies for authentication."""

from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.errors import unauthorized
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    """Resolve the caller from a bearer token, or raise 401."""
    token = credentials.credentials if credentials else request.query_params.get("token", "")
    if not token:
        raise unauthorized()
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise unauthorized("That sign in token is not valid") from None
    return payload


def get_user_actor(actor: dict[str, Any] = Depends(get_actor)) -> dict[str, Any]:
    if actor.get("scope") != "user":
        raise unauthorized("A host account is required for that action")
    return actor
