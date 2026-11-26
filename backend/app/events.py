"""Event bus and presence store.

Room events are published to a channel per room. With Redis configured the
messages travel through Redis pub and sub, so a vote handled by one API
process reaches clients connected to another process. Without Redis the bus
falls back to process memory, which is handy for tests and local trials.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def display_id(key: str) -> str:
    """Opaque per-participant display id derived from the internal key.

    The internal key is a user ID or guest subject and must never reach
    clients; a truncated hash is stable for list rendering but reveals
    nothing about the underlying identity.
    """
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class Subscription:
    """A bounded queue that receives messages for one room channel.

    The bound is the slow-consumer policy: a client that stops reading can
    hold at most subscription_queue_maxsize (default 50) room-state
    messages. On overflow the oldest queued message is dropped, because
    every message is a full state snapshot and only the latest matters.
    This class backs both the in-memory bus and the Redis bus fan-out, so
    the bound applies to both.
    """

    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.queue: asyncio.Queue[str] = asyncio.Queue(
            maxsize=get_settings().subscription_queue_maxsize
        )
        self.loop = asyncio.get_running_loop()
        self.dropped = 0

    def _put_bounded(self, message: str) -> None:
        try:
            self.queue.put_nowait(message)
            return
        except asyncio.QueueFull:
            pass
        self.dropped += 1
        try:
            self.queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

    def deliver(self, message: str) -> None:
        if self.loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self._put_bounded(message)
        else:
            self.loop.call_soon_threadsafe(self._put_bounded, message)


class EventBus:
    """Interface shared by the Redis and in memory implementations."""

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    async def subscribe(self, channel: str) -> Subscription:
        raise NotImplementedError

    async def unsubscribe(self, subscription: Subscription) -> None:
        raise NotImplementedError

    async def set_presence(self, room_code: str, key: str, name: str, is_host: bool) -> None:
        raise NotImplementedError

    async def remove_presence(self, room_code: str, key: str) -> None:
        raise NotImplementedError

    async def get_presence(self, room_code: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class MemoryBus(EventBus):
    def __init__(self) -> None:
        self._subs: dict[str, set[Subscription]] = {}
        self._presence: dict[str, dict[str, dict[str, Any]]] = {}

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        for sub in list(self._subs.get(channel, set())):
            sub.deliver(message)

    async def subscribe(self, channel: str) -> Subscription:
        sub = Subscription(channel)
        self._subs.setdefault(channel, set()).add(sub)
        return sub

    async def unsubscribe(self, subscription: Subscription) -> None:
        self._subs.get(subscription.channel, set()).discard(subscription)

    async def set_presence(self, room_code: str, key: str, name: str, is_host: bool) -> None:
        # Same expiry semantics as the Redis bus: each participant's entry
        # carries its own deadline, refreshed only by that participant.
        self._presence.setdefault(room_code, {})[key] = {
            "name": name,
            "is_host": is_host,
            "expires_at": time.monotonic() + get_settings().presence_ttl_seconds,
        }

    async def remove_presence(self, room_code: str, key: str) -> None:
        self._presence.get(room_code, {}).pop(key, None)

    async def get_presence(self, room_code: str) -> list[dict[str, Any]]:
        now = time.monotonic()
        room = self._presence.get(room_code, {})
        for key in [k for k, item in room.items() if item["expires_at"] <= now]:
            room.pop(key, None)
        return [
            {"id": display_id(key), "name": item["name"], "is_host": item["is_host"]}
            for key, item in room.items()
        ]


class RedisBus(EventBus):
    """Redis pub and sub with one shared subscription connection per process.

    Every room channel is multiplexed over a single pubsub connection and
    fanned out to local subscribers. Opening one connection per client does
    not scale, so this class never does that.
    """

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(redis_url, decode_responses=True, max_connections=1024)
        self._pubsub = self._redis.pubsub()
        self._local: dict[str, set[Subscription]] = {}
        self._pump_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(payload))

    async def _ensure_pump(self) -> None:
        if self._pump_task is not None:
            return

        async def pump() -> None:
            while True:
                try:
                    channels = [c for c, members in self._local.items() if members]
                    if not channels:
                        await asyncio.sleep(0.2)
                        continue
                    await self._pubsub.subscribe(*channels)
                    async for message in self._pubsub.listen():
                        if message.get("type") != "message":
                            continue
                        channel = str(message["channel"])
                        for sub in list(self._local.get(channel, set())):
                            sub.deliver(str(message["data"]))
                except asyncio.CancelledError:
                    return
                except Exception:
                    logger.exception("Event bus pump failed. Reconnecting.")
                    await asyncio.sleep(0.5)

        self._pump_task = asyncio.create_task(pump())

    async def subscribe(self, channel: str) -> Subscription:
        sub = Subscription(channel)
        async with self._lock:
            first = channel not in self._local or not self._local[channel]
            self._local.setdefault(channel, set()).add(sub)
            await self._ensure_pump()
            if first:
                await self._pubsub.subscribe(channel)
        return sub

    async def unsubscribe(self, subscription: Subscription) -> None:
        async with self._lock:
            members = self._local.get(subscription.channel, set())
            members.discard(subscription)
            if not members:
                try:
                    await self._pubsub.unsubscribe(subscription.channel)
                except Exception:
                    logger.warning("Pubsub unsubscribe failed", exc_info=True)

    @staticmethod
    def _presence_key(room_code: str, key: str) -> str:
        return f"presence:{room_code}:{key}"

    async def set_presence(self, room_code: str, key: str, name: str, is_host: bool) -> None:
        # One Redis key per participant, each with its own short TTL
        # (presence_ttl_seconds, default 300 seconds). Only this
        # participant's own join or activity refreshes this key, so a
        # crashed session's ghost expires within the TTL and a new join in
        # the room can never resurrect or extend a stale participant.
        value = json.dumps({"name": name, "is_host": is_host})
        await self._redis.set(
            self._presence_key(room_code, key),
            value,
            ex=get_settings().presence_ttl_seconds,
        )

    async def remove_presence(self, room_code: str, key: str) -> None:
        await self._redis.delete(self._presence_key(room_code, key))

    async def get_presence(self, room_code: str) -> list[dict[str, Any]]:
        prefix = f"presence:{room_code}:"
        people = []
        async for redis_key in self._redis.scan_iter(match=f"{prefix}*"):
            value = await self._redis.get(redis_key)
            if value is None:
                continue
            item = json.loads(value)
            key = redis_key[len(prefix) :]
            people.append({"id": display_id(key), "name": item["name"], "is_host": item["is_host"]})
        return people


def create_bus() -> EventBus:
    if settings.event_bus == "redis":
        try:
            import redis as redis_lib

            client = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=1)
            client.ping()
            client.close()
            logger.info("Event bus: Redis at %s", settings.redis_url)
            return RedisBus(settings.redis_url)
        except Exception:
            logger.warning("Redis is not reachable. Falling back to the in memory event bus.")
    logger.info("Event bus: in memory")
    return MemoryBus()


bus: EventBus = create_bus()
