"""Event bus and presence store.

Room events are published to a channel per room. With Redis configured the
messages travel through Redis pub and sub, so a vote handled by one API
process reaches clients connected to another process. Without Redis the bus
falls back to process memory, which is handy for tests and local trials.
"""

import asyncio
import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Subscription:
    """A queue that receives messages for one room channel."""

    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.loop = asyncio.get_running_loop()

    def deliver(self, message: str) -> None:
        if self.loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self.queue.put_nowait(message)
        else:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, message)


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
        self._presence.setdefault(room_code, {})[key] = {"name": name, "is_host": is_host}

    async def remove_presence(self, room_code: str, key: str) -> None:
        self._presence.get(room_code, {}).pop(key, None)

    async def get_presence(self, room_code: str) -> list[dict[str, Any]]:
        return [
            {"key": key, "name": item["name"], "is_host": item["is_host"]}
            for key, item in self._presence.get(room_code, {}).items()
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

    async def set_presence(self, room_code: str, key: str, name: str, is_host: bool) -> None:
        value = json.dumps({"name": name, "is_host": is_host})
        await self._redis.hset(f"presence:{room_code}", key, value)
        await self._redis.expire(f"presence:{room_code}", 60 * 60 * 12)

    async def remove_presence(self, room_code: str, key: str) -> None:
        await self._redis.hdel(f"presence:{room_code}", key)

    async def get_presence(self, room_code: str) -> list[dict[str, Any]]:
        raw = await self._redis.hgetall(f"presence:{room_code}")
        people = []
        for key, value in raw.items():
            item = json.loads(value)
            people.append({"key": key, "name": item["name"], "is_host": item["is_host"]})
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
