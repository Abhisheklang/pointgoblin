"""Small fixed window rate limiter backed by Redis or process memory."""

import time

from app.config import get_settings
from app.errors import AppError

settings = get_settings()


class RateLimiter:
    """Counts requests per key inside a rolling window."""

    def __init__(self) -> None:
        self._memory: dict[str, list[float]] = {}
        self._redis = None
        if settings.event_bus == "redis":
            try:
                import redis as redis_lib

                self._redis = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=1)
                self._redis.ping()
            except Exception:
                self._redis = None

    def check(self, key: str, limit: int) -> None:
        """Raise a 429 AppError when the key has used up its allowance."""
        if not settings.rate_limit_enabled:
            return
        now = time.time()
        window = settings.rate_window_seconds
        if self._redis is not None:
            redis_key = f"ratelimit:{key}"
            count = int(self._redis.incr(redis_key))
            if count == 1:
                self._redis.expire(redis_key, window)
            if count > limit:
                raise AppError(429, "rate_limited", "Too many requests. Please wait a moment.")
            return
        hits = [t for t in self._memory.get(key, []) if now - t < window]
        if len(hits) >= limit:
            raise AppError(429, "rate_limited", "Too many requests. Please wait a moment.")
        hits.append(now)
        self._memory[key] = hits


limiter = RateLimiter()
