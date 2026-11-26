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
