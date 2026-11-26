"""Live room behaviour over WebSockets."""

import json

from conftest import auth_headers


def test_two_clients_see_each_other_vote_and_reveal(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "Live story"}, headers=headers)
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Wendy Watcher"}).json()

    def latest_state(socket, minimum_votes: int) -> dict:
        while True:
            state = json.loads(socket.receive_text())
            if state.get("round") and state["round"]["vote_count"] >= minimum_votes:
                return state

    with (
        client.websocket_connect(f"/ws/rooms/{code}?token={host['access_token']}") as host_socket,
        client.websocket_connect(f"/ws/rooms/{code}?token={guest['access_token']}") as guest_socket,
    ):
        latest_state(host_socket, 0)
        guest_socket.send_text(json.dumps({"action": "vote", "value": "5"}))
        seen_by_host = latest_state(host_socket, 1)
        assert seen_by_host["round"]["vote_count"] == 1
        assert seen_by_host["round"]["results"] is None
        names = [p["name"] for p in seen_by_host["participants"]]
        assert "Wendy Watcher" in names
        host_socket.send_text(json.dumps({"action": "reveal"}))
        revealed = None
        while revealed is None:
            state = json.loads(guest_socket.receive_text())
            if state.get("round") and state["round"]["revealed"]:
                revealed = state
        assert revealed["round"]["results"]["average"] == 5.0


def test_non_object_message_does_not_kill_the_socket(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "Sturdy"}, headers=headers)
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Ned Robust"}).json()
    with client.websocket_connect(
        f"/ws/rooms/{code}?token={guest['access_token']}"
    ) as guest_socket:
        guest_socket.receive_text()
        for junk in ("123", "[]", '"x"', "not json"):
            guest_socket.send_text(junk)
        guest_socket.send_text(json.dumps({"action": "vote", "value": "5"}))
        state = {}
        while True:
            state = json.loads(guest_socket.receive_text())
            if state.get("round") and state["round"]["vote_count"] == 1:
                break
        assert state["round"]["vote_count"] == 1


def test_message_rate_limiter_allows_up_to_the_limit():
    from app.ws import MessageRateLimiter

    limiter = MessageRateLimiter(limit=3, window_seconds=60)
    assert limiter.allow()
    assert limiter.allow()
    assert limiter.allow()
    assert not limiter.allow()


def test_oversized_message_is_ignored_and_socket_survives(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "Big"}, headers=headers)
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Omar Large"}).json()
    with client.websocket_connect(
        f"/ws/rooms/{code}?token={guest['access_token']}"
    ) as guest_socket:
        guest_socket.receive_text()
        guest_socket.send_text("x" * (70 * 1024))
        guest_socket.send_text(json.dumps({"action": "vote", "value": "2"}))
        while True:
            state = json.loads(guest_socket.receive_text())
            if state.get("round") and state["round"]["vote_count"] == 1:
                break
        assert state["round"]["vote_count"] == 1


def test_websocket_rejects_a_bad_token(client, host_and_room):
    _, room = host_and_room
    code = room["room"]["code"]
    try:
        with client.websocket_connect(f"/ws/rooms/{code}?token=not-a-token") as socket:
            socket.receive_text()
        raised = False
    except Exception:
        raised = True
    assert raised


def test_guest_socket_cannot_reveal(client, host_and_room):
    import time

    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "Guarded"}, headers=headers)
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Gary Guest"}).json()
    with client.websocket_connect(
        f"/ws/rooms/{code}?token={guest['access_token']}"
    ) as guest_socket:
        guest_socket.send_text(json.dumps({"action": "vote", "value": "3"}))
        guest_socket.send_text(json.dumps({"action": "reveal"}))
        state = {}
        for _ in range(20):
            state = client.get(
                f"/api/rooms/{code}", headers=auth_headers(guest["access_token"])
            ).json()
            if state["round"] and state["round"]["vote_count"] == 1:
                break
            time.sleep(0.1)
        time.sleep(0.5)
        state = client.get(f"/api/rooms/{code}", headers=auth_headers(guest["access_token"])).json()
        assert state["round"]["vote_count"] == 1
        assert state["round"]["revealed"] is False
