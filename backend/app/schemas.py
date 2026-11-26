"""Request and response schemas."""

import re

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# bcrypt hashes at most 72 bytes of password; bcrypt 5.x raises ValueError
# past that instead of truncating. The cap is on UTF-8 byte length, not
# character count, so a multibyte password counts every byte it encodes to.
MAX_PASSWORD_BYTES = 72


def check_password_byte_length(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 bytes")
    return value


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value.lower()

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return check_password_byte_length(value)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        return check_password_byte_length(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class JoinRoomRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    name: str = Field(min_length=1, max_length=80)


class CreateStoryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def check_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Story title must not be blank")
        return value


class VoteRequest(BaseModel):
    value: str = Field(min_length=1, max_length=8)


class RoomResponse(BaseModel):
    code: str
    name: str
    host_name: str | None = None
