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
