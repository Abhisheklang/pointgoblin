"""Registration and sign in routes."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import repositories, schemas, services
from app.config import get_settings
from app.database import get_db
from app.errors import unauthorized
from app.rate_limit import limiter
from app.security import create_user_token, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(
    payload: schemas.RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> schemas.TokenResponse:
    limiter.check(
        f"auth:{request.client.host if request.client else 'unknown'}",
        get_settings().auth_rate_limit,
    )
    user = services.register_user(db, payload.email, payload.name, hash_password(payload.password))
    logger.info("New host account registered for %s", payload.email)
    return schemas.TokenResponse(access_token=create_user_token(user.id, user.name), name=user.name)


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)
) -> schemas.TokenResponse:
    limiter.check(
        f"auth:{request.client.host if request.client else 'unknown'}",
        get_settings().auth_rate_limit,
    )
    user = repositories.get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise unauthorized("Email or password is not correct")
    return schemas.TokenResponse(access_token=create_user_token(user.id, user.name), name=user.name)
