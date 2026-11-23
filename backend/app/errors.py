"""Structured application errors."""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """An error that maps cleanly onto an HTTP response."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def not_found(message: str = "The requested resource was not found") -> AppError:
    return AppError(404, "not_found", message)


def forbidden(message: str = "You do not have permission to do that") -> AppError:
    return AppError(403, "forbidden", message)


def bad_request(message: str) -> AppError:
    return AppError(400, "bad_request", message)


def unauthorized(message: str = "Sign in is required") -> AppError:
    return AppError(401, "unauthorized", message)
