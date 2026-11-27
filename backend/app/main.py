"""Application entry point."""

import logging
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.config import get_settings
from app.database import init_db
from app.errors import AppError, app_error_handler
from app.routes import auth, rooms
from app.ws import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    logger.info("%s API is ready", settings.app_name)
    yield


def _json_safe(value: Any) -> Any:
    """Replace non-finite floats with their text form, recursively.

    Python's JSON parser accepts Infinity, NaN and overflowing literals
    such as 1e999. When one lands in a field that fails validation, the
    422 detail embeds the value, and rendering that detail raises
    ValueError (out of range float values are not JSON compliant), which
    turned a malformed payload into an unhandled 500 (PG-A3). Rendering
    the value as text keeps the response a plain 422.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = _json_safe(jsonable_encoder(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": detail})


# Baseline security headers for every HTTP response (PG-A5). The API
# serves JSON only, so frame denial costs nothing; the websocket upgrade
# is not an HTTP response and is untouched by this middleware.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response


def _too_large_response() -> StarletteResponse:
    return JSONResponse(
        status_code=413,
        content={
            "error": {
                "code": "payload_too_large",
                "message": "That request body is too large.",
            }
        },
    )


class BodySizeLimitMiddleware:
    """Refuse oversized HTTP request bodies before they are parsed (PG-S2).

    Pure ASGI middleware. A declared Content-Length over the cap is
    refused without reading the body at all. Otherwise the body is
    streamed and counted as it arrives, and the request is refused the
    moment it passes the cap, so at most the cap plus one chunk is ever
    held in memory; bodies within the cap are replayed to the app
    unchanged. Websocket scopes pass through untouched (the socket has
    its own message size limit).
    """

    def __init__(self, app: Any, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        declared = headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await _too_large_response()(scope, receive, send)
                    return
            except ValueError:
                pass
        body = b""
        more_body = True
        pending: list[Any] = []
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                # A disconnect or other message: stop reading the body and
                # hand the app this message first, then the rest of the
                # stream as it arrives.
                pending.append(message)
                break
            body += message.get("body", b"")
            if len(body) > self.max_bytes:
                await _too_large_response()(scope, receive, send)
                return
            more_body = message.get("more_body", False)
        delivered = False

        async def replay_receive() -> Any:
            nonlocal delivered
            if pending:
                return pending.pop(0)
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)


# The interactive docs and the OpenAPI schema are development aids.
# Outside dev mode they would hand the full endpoint inventory and every
# schema to unauthenticated callers, so they are not mounted at all
# (SEC7/PG-S1).
if settings.environment == "dev":
    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"
else:
    docs_url = redoc_url = openapi_url = None

app = FastAPI(
    title="PointGoblin API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Body size cap (PG-S2), added before the security headers middleware so
# it runs inside it and its 413 responses still carry the headers.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
# Added last so it runs outermost and also covers CORS preflight and
# error responses.
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(auth.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
