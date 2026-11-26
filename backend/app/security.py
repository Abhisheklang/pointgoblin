"""Password hashing and JSON Web Token helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a plain text password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain text password against a stored hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Precomputed bcrypt hash of a throwaway password. The login route verifies
# against this when the email is unknown, so the unknown-email path pays the
# same bcrypt cost as the wrong-password path and response timing no longer
# reveals whether an account exists.
DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"dummy-password-for-timing-parity", bcrypt.gensalt()).decode()


def create_token(subject: str, name: str, scope: str, minutes: int, room_code: str = "") -> str:
    """Create a signed access token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "name": name,
        "scope": scope,
        "room": room_code,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a signed access token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def create_user_token(user_id: str, name: str) -> str:
    return create_token(user_id, name, "user", settings.access_token_minutes)


def create_guest_token(room_code: str, name: str) -> str:
    # The random component keeps two guests who typed the same display name
    # as separate identities; the name lives only in the name claim.
    subject = f"guest:{room_code}:{uuid4().hex}"
    return create_token(subject, name, "guest", settings.guest_token_minutes, room_code)
