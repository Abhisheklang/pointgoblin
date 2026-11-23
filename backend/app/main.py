"""Application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="PointGoblin API", version="1.0.0")
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(ws_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("%s API is ready", settings.app_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
