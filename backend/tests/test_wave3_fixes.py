"""Wave 3 vibe audit fixes: regression tests for the confirmed findings."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_sec1_env_example_placeholder_is_rejected_outside_dev_mode():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="replace-with-a-long-random-value")


def test_sec1_replacement_placeholder_is_rejected_outside_dev_mode():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="REPLACE_ME_generate_a_random_secret_locally_do_not_commit")


def test_sec3_query_string_token_is_not_accepted(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    response = client.get(f"/api/rooms/{code}?token={host['access_token']}")
    assert response.status_code == 401
    header = client.get(
        f"/api/rooms/{code}", headers={"Authorization": f"Bearer {host['access_token']}"}
    )
    assert header.status_code == 200


def test_sec2_rest_room_mutations_are_rate_limited(client, host_and_room, monkeypatch):
    from app.config import get_settings

    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "room_mutation_rate_limit", 3)
    statuses = [
        client.post(
            f"/api/rooms/{code}/stories", json={"title": f"Story {index}"}, headers=headers
        ).status_code
        for index in range(4)
    ]
    assert statuses[:3] == [201, 201, 201]
    assert statuses[3] == 429


def test_v2_blank_story_title_is_rejected_over_rest(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    response = client.post(f"/api/rooms/{code}/stories", json={"title": "   "}, headers=headers)
    assert response.status_code == 422


def test_v2_v3_blank_story_over_websocket_gets_an_error_frame(client, host_and_room):
    import json

    host, room = host_and_room
    code = room["room"]["code"]
    with client.websocket_connect(f"/ws/rooms/{code}?token={host['access_token']}") as socket:
        socket.receive_text()
        socket.send_text(json.dumps({"action": "add_story", "title": "   "}))
        frame = {}
        for _ in range(10):
            frame = json.loads(socket.receive_text())
            if frame.get("type") == "error":
                break
        assert frame.get("type") == "error"
    state = client.get(
        f"/api/rooms/{code}", headers={"Authorization": f"Bearer {host['access_token']}"}
    ).json()
    assert state["stories"] == []


def test_v3_refused_action_gets_an_error_frame(client, host_and_room):
    import json

    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    client.post(f"/api/rooms/{code}/stories", json={"title": "Guarded"}, headers=headers)
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Gary Guest"}).json()
    with client.websocket_connect(f"/ws/rooms/{code}?token={guest['access_token']}") as socket:
        socket.receive_text()
        socket.send_text(json.dumps({"action": "reveal"}))
        frame = {}
        for _ in range(10):
            frame = json.loads(socket.receive_text())
            if frame.get("type") == "error":
                break
        assert frame.get("type") == "error"
        assert "host" in frame["message"].lower()


def test_u2_voted_state_is_keyed_by_participant_id_not_name(client, host_and_room):
    from app.events import display_id
    from app.security import decode_token

    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    client.post(f"/api/rooms/{code}/stories", json={"title": "Story"}, headers=headers)
    first = client.post("/api/rooms/join", json={"code": code, "name": "Sam Same"}).json()
    second = client.post("/api/rooms/join", json={"code": code, "name": "Sam Same"}).json()
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    state = client.post(
        f"/api/rooms/{code}/vote", json={"value": "5"}, headers=first_headers
    ).json()
    expected_id = display_id(decode_token(first["access_token"])["sub"])
    other_id = display_id(decode_token(second["access_token"])["sub"])
    assert expected_id != other_id
    assert state["round"]["voted"] == [expected_id]
    revealed = client.post(f"/api/rooms/{code}/reveal", headers=headers).json()
    votes = revealed["round"]["results"]["votes"]
    assert [vote["id"] for vote in votes] == [expected_id]


def test_k4_story_cap_is_enforced(client, host_and_room, monkeypatch):
    from app.config import get_settings

    host, room = host_and_room
    code = room["room"]["code"]
    headers = {"Authorization": f"Bearer {host['access_token']}"}
    monkeypatch.setattr(get_settings(), "max_stories_per_room", 1)
    first = client.post(f"/api/rooms/{code}/stories", json={"title": "One"}, headers=headers)
    assert first.status_code == 201
    second = client.post(f"/api/rooms/{code}/stories", json={"title": "Two"}, headers=headers)
    assert second.status_code == 400


def test_sec1_placeholders_still_work_in_dev_mode():
    settings = Settings(
        jwt_secret="replace-with-a-long-random-value",
        environment="dev",
    )
    assert settings.environment == "dev"
