"""Wave 5 suspect verdict fixes: regression tests for the proven findings."""

import pytest
from conftest import auth_headers


def _register_stranger(client, email="stranger@example.com"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Stranger B", "password": "password123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _host_with_story(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    response = client.post(
        f"/api/rooms/{code}/stories", json={"title": "Story One"}, headers=headers
    )
    assert response.status_code == 201, response.text
    return host, code, headers


# ---- SEC6: user tokens need room membership ----


def test_sec6_non_member_user_cannot_read_room(client, host_and_room):
    _host, code, _headers = _host_with_story(client, host_and_room)
    stranger = _register_stranger(client)
    response = client.get(f"/api/rooms/{code}", headers=auth_headers(stranger["access_token"]))
    assert response.status_code == 403


def test_sec6_non_member_user_cannot_vote(client, host_and_room):
    host, code, headers = _host_with_story(client, host_and_room)
    stranger = _register_stranger(client)
    response = client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "5"},
        headers=auth_headers(stranger["access_token"]),
    )
    assert response.status_code == 403
    state = client.get(f"/api/rooms/{code}", headers=headers).json()
    assert state["round"]["vote_count"] == 0


def test_sec6_non_member_user_websocket_is_refused(client, host_and_room):
    _host, code, _headers = _host_with_story(client, host_and_room)
    stranger = _register_stranger(client)
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            f"/ws/rooms/{code}?token={stranger['access_token']}"
        ) as socket:
            socket.receive_text()
    assert excinfo.value.code == 4403


def test_sec6_member_user_can_read_and_vote(client, host_and_room):
    _host, code, _headers = _host_with_story(client, host_and_room)
    member = _register_stranger(client, email="member@example.com")
    # Joining while signed in records the membership.
    joined = client.post(
        "/api/rooms/join",
        json={"code": code, "name": "Stranger B"},
        headers=auth_headers(member["access_token"]),
    )
    assert joined.status_code == 200, joined.text
    headers = auth_headers(member["access_token"])
    state = client.get(f"/api/rooms/{code}", headers=headers)
    assert state.status_code == 200
    voted = client.post(f"/api/rooms/{code}/vote", json={"value": "5"}, headers=headers)
    assert voted.status_code == 200
    assert voted.json()["round"]["vote_count"] == 1


def test_sec6_host_still_reads_and_votes_and_reveal_stays_host_only(client, host_and_room):
    host, code, headers = _host_with_story(client, host_and_room)
    assert client.get(f"/api/rooms/{code}", headers=headers).status_code == 200
    voted = client.post(f"/api/rooms/{code}/vote", json={"value": "8"}, headers=headers)
    assert voted.status_code == 200
    # Control that held before the fix: a guest in the room cannot reveal.
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Gus Guest"}).json()
    reveal = client.post(f"/api/rooms/{code}/reveal", headers=auth_headers(guest["access_token"]))
    assert reveal.status_code == 403
    # Control that held before the fix: a guest token for this room gets a
    # 403 on a different room.
    other = client.post("/api/rooms", json={"name": "Other room"}, headers=headers).json()
    cross = client.get(
        f"/api/rooms/{other['room']['code']}",
        headers=auth_headers(guest["access_token"]),
    )
    assert cross.status_code == 403


# ---- PG-S2: HTTP body size limit ----


def test_pg_s2_oversized_login_body_is_refused_with_413(client):
    body = b'{"email": "a@b.com", "password": "' + b"x" * (200 * 1024) + b'"}'
    response = client.post(
        "/api/auth/login", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_pg_s2_oversized_chunked_body_is_refused_with_413(client):
    def chunks():
        yield b'{"email": "a@b.com", "password": "'
        for _ in range(20):
            yield b"x" * 8192
        yield b'"}'

    response = client.post(
        "/api/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_pg_s2_normal_bodies_still_work(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    login = client.post(
        "/api/auth/login",
        json={"email": "host@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    story = client.post(
        f"/api/rooms/{code}/stories",
        json={"title": "A perfectly normal story title"},
        headers=auth_headers(host["access_token"]),
    )
    assert story.status_code == 201


# ---- SEC5: rate limiter fails degraded, expiry attached at creation ----
# These use hand rolled Redis stand-ins, the same pattern as the wave 2
# S5 tests; the fakeredis runs are the verdict pass reproducers, labelled
# as fakeredis in the wave 5 report (no redis-server exists in this VM).


class _SyncFakeRedis:
    """Sync Redis stand-in tracking values and TTLs like real Redis."""

    def __init__(self):
        self.store = {}
        self.ttls = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = int(value)
        self.ttls[key] = ex
        return True

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def ttl(self, key):
        if key not in self.store:
            return -2
        return -1 if self.ttls.get(key) is None else self.ttls[key]


def _limiter_with(redis_client):
    from app.rate_limit import RateLimiter

    limiter = RateLimiter.__new__(RateLimiter)
    limiter._memory = {}
    limiter._redis = redis_client
    return limiter


def test_sec5_counter_key_always_has_a_ttl(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    fake = _SyncFakeRedis()
    limiter = _limiter_with(fake)
    for _ in range(3):
        limiter.check("auth:9.9.9.9", 100)
    assert fake.store["ratelimit:auth:9.9.9.9"] == 3
    # Never -1: the key was created with its expiry already attached.
    assert fake.ttl("ratelimit:auth:9.9.9.9") > 0


def test_sec5_redis_drop_falls_back_to_memory_limiter(monkeypatch):
    import redis as redis_lib

    from app.config import get_settings
    from app.errors import AppError

    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)

    class DeadRedis:
        def set(self, *args, **kwargs):
            raise redis_lib.exceptions.ConnectionError("redis went away")

        def incr(self, *args, **kwargs):
            raise redis_lib.exceptions.ConnectionError("redis went away")

    limiter = _limiter_with(DeadRedis())
    # No exception escapes check(): the fallback memory limiter answers.
    for _ in range(3):
        limiter.check("auth:1.2.3.4", 3)
    with pytest.raises(AppError) as excinfo:
        limiter.check("auth:1.2.3.4", 3)
    assert excinfo.value.status_code == 429
