"""Small fixed window rate limiter backed by Redis or process memory."""

import logging
import time

from app.config import get_settings
from app.errors import AppError

logger = logging.getLogger(__name__)
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
                # Log the cause: silently degrading to the per-process
                # memory limiter leaves operators no trace of a broken
                # REDIS_URL or an unreachable Redis (V7).
                logger.warning(
                    "Redis rate limiter is not reachable. "
                    "Falling back to the in memory rate limiter.",
                    exc_info=True,
                )
                self._redis = None

    def _check_memory(self, key: str, limit: int, now: float, window: int) -> None:
        hits = [t for t in self._memory.get(key, []) if now - t < window]
        if len(hits) >= limit:
            raise AppError(429, "rate_limited", "Too many requests. Please wait a moment.")
        hits.append(now)
        self._memory[key] = hits

    def check(self, key: str, limit: int) -> None:
        """Raise a 429 AppError when the key has used up its allowance."""
        if not settings.rate_limit_enabled:
            return
        now = time.time()
        window = settings.rate_window_seconds
        if self._redis is not None:
            redis_key = f"ratelimit:{key}"
            try:
                # Create the counter with its expiry already attached, in
                # one command, then increment (SEC5). The old code issued
                # INCR and EXPIRE as two calls and only expired when the
                # count was exactly 1, so a single lost EXPIRE left the
                # key with no TTL and the client was rate limited forever.
                # Here the key can never exist without a TTL: the SET NX
                # creates it with the window expiry, and INCR preserves
                # the TTL of an existing key.
                self._redis.set(redis_key, 0, ex=window, nx=True)
                count = int(self._redis.incr(redis_key))
            except Exception:
                # Redis dropped after the import time probe (SEC5): fail
                # degraded into the local memory limiter instead of
                # raising, which turned register, login, join and room
                # creation into unhandled 500s. The fallback still limits,
                # just per process, so the failure is neither a 500 nor a
                # wide open limiter.
                logger.warning(
                    "Redis rate limiter failed. Falling back to the in memory "
                    "rate limiter for this check.",
                    exc_info=True,
                )
                self._check_memory(key, limit, now, window)
                return
            if count > limit:
                raise AppError(429, "rate_limited", "Too many requests. Please wait a moment.")
            return
        self._check_memory(key, limit, now, window)


limiter = RateLimiter()
