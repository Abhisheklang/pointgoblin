"""Wave 4 advanced audit fixes: regression tests for the confirmed findings."""

import asyncio
import json
import time

from app.config import get_settings


def _join_guest(client, code, name="Gary Guest"):
    response = client.post("/api/rooms/join", json={"code": code, "name": name})
    assert response.status_code == 200, response.text
    return response.json()


def _participant_names(client, host, code):
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    state = client.get(f"/api/rooms/{code}", headers=headers).json()
    return [person["name"] for person in state["participants"]]


def test_pg_a1_live_participant_stays_present_past_the_ttl(client, host_and_room, monkeypatch):
    host, room = host_and_room
    code = room["room"]["code"]
    monkeypatch.setattr(get_settings(), "presence_ttl_seconds", 2)
    guest = _join_guest(client, code)
    with client.websocket_connect(f"/ws/rooms/{code}?token={guest['access_token']}") as socket:
        socket.receive_text()
        # Well past the 2 second TTL, with the socket open the whole time.
        time.sleep(3.5)
        assert "Gary Guest" in _participant_names(client, host, code)


def test_pg_a1_unrefreshed_presence_still_expires_at_the_ttl(monkeypatch):
    from app.events import MemoryBus

    monkeypatch.setattr(get_settings(), "presence_ttl_seconds", 1)
    bus = MemoryBus()

    async def scenario():
        await bus.set_presence("ROOM42", "guest:ROOM42:abc", "Ghost Guest", False)
        present = await bus.get_presence("ROOM42")
        await asyncio.sleep(1.3)
        expired = await bus.get_presence("ROOM42")
        return present, expired

    present, expired = asyncio.run(scenario())
    assert [person["name"] for person in present] == ["Ghost Guest"]
    assert expired == []


def test_pg_a1_disconnected_participant_leaves_the_list(client, host_and_room, monkeypatch):
    host, room = host_and_room
    code = room["room"]["code"]
    monkeypatch.setattr(get_settings(), "presence_ttl_seconds", 2)
    guest = _join_guest(client, code, name="Leaving Guest")
    with client.websocket_connect(f"/ws/rooms/{code}?token={guest['access_token']}") as socket:
        socket.receive_text()
        assert "Leaving Guest" in _participant_names(client, host, code)
    assert "Leaving Guest" not in _participant_names(client, host, code)


def test_pg_a2_binary_frame_does_not_kill_the_connection(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    client.post(f"/api/rooms/{code}/stories", json={"title": "Binary proof"}, headers=headers)
    guest = _join_guest(client, code, name="Binary Guest")
    with client.websocket_connect(f"/ws/rooms/{code}?token={guest['access_token']}") as socket:
        socket.receive_text()
        socket.send_bytes(b"\x00\x01binary")
        socket.send_text(json.dumps({"action": "vote", "value": "5"}))
        state = {}
        for _ in range(20):
            state = json.loads(socket.receive_text())
            if state.get("round") and state["round"]["vote_count"] == 1:
                break
        assert state["round"]["vote_count"] == 1


def test_pg_a3_nonfinite_float_in_login_payload_returns_422_not_500(client):
    response = client.post(
        "/api/auth/login",
        content=b'{"email": "a@b.com", "password": 1e999}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_pg_a3_nan_in_register_payload_returns_422_not_500(client):
    response = client.post(
        "/api/auth/register",
        content=b'{"email": "n@b.com", "name": NaN, "password": "password123"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_pg_a3_infinity_in_register_payload_returns_422_not_500(client):
    response = client.post(
        "/api/auth/register",
        content=b'{"email": "i@b.com", "name": "Ivy", "password": Infinity}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_pg_a4_email_with_trailing_newline_is_rejected(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com\n", "name": "Two", "password": "password123"},
    )
    assert response.status_code == 422


def test_pg_a4_newline_twin_cannot_register_as_a_second_account(client):
    first = client.post(
        "/api/auth/register",
        json={"email": "twin@example.com", "name": "One", "password": "password123"},
    )
    assert first.status_code == 201
    twin = client.post(
        "/api/auth/register",
        json={"email": "twin@example.com\n", "name": "Two", "password": "password123"},
    )
    assert twin.status_code == 422
    login_twin = client.post(
        "/api/auth/login", json={"email": "twin@example.com\n", "password": "password123"}
    )
    assert login_twin.status_code in (401, 422)


def test_pg_a4_email_with_surrounding_whitespace_is_rejected(client):
    for email in (" pad@example.com", "pad@example.com ", "pad@example.com\t"):
        response = client.post(
            "/api/auth/register",
            json={"email": email, "name": "Pad", "password": "password123"},
        )
        assert response.status_code == 422, email


def test_pg_a5_security_headers_on_health_and_api_responses(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    for response in (
        client.get("/health"),
        client.get(f"/api/rooms/{code}", headers=headers),
        client.get("/api/rooms/NOPE99", headers=headers),
    ):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
