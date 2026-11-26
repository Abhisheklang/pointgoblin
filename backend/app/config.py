"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_DEFAULT_JWT_SECRETS = {
    "change-me-in-production",
    "local-development-secret-change-me",
}


class Settings(BaseSettings):
    """Runtime configuration. Secrets come from the environment only."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PointGoblin"
    environment: str = "production"
    allow_insecure_jwt_secret: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pointgoblin"
    redis_url: str = "redis://localhost:6379/0"
    event_bus: str = "redis"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    guest_token_minutes: int = 60 * 12
    rate_limit_enabled: bool = True
    auth_rate_limit: int = 20
    room_rate_limit: int = 10
    rate_window_seconds: int = 60
    ws_message_rate_limit: int = 120
    ws_max_message_bytes: int = 64 * 1024
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    @model_validator(mode="after")
    def reject_known_default_jwt_secret(self) -> "Settings":
        """Fail closed on a shipped default secret outside explicit dev mode."""
        dev_mode = self.environment == "dev" or self.allow_insecure_jwt_secret
        if self.jwt_secret in KNOWN_DEFAULT_JWT_SECRETS and not dev_mode:
            raise ValueError(
                "JWT_SECRET is set to a known default value. Set JWT_SECRET to a "
                "strong random secret, or set ENVIRONMENT=dev (or "
                "ALLOW_INSECURE_JWT_SECRET=true) for local development only."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
