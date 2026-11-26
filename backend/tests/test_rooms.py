"""Room joining, stories and permissions."""

from conftest import auth_headers, make_room, register_host


def join_guest(client, code: str, name: str = "Gus Guest") -> dict:
    response = client.post("/api/rooms/join", json={"code": code, "name": name})
    assert response.status_code == 200, response.text
    return response.json()


def test_guest_joins_with_a_room_code(client, host_and_room):
    _, room = host_and_room
    joined = join_guest(client, room["room"]["code"])
    assert joined["access_token"]
    assert joined["room"]["code"] == room["room"]["code"]


def test_joining_an_unknown_room_fails(client):
    response = client.post("/api/rooms/join", json={"code": "ZZZZZZ", "name": "Nobody"})
    assert response.status_code == 404


def test_host_adds_a_story_and_it_becomes_active(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    response = client.post(
        f"/api/rooms/{code}/stories",
        json={"title": "As a user I can reset my password"},
        headers=auth_headers(host["access_token"]),
    )
    assert response.status_code == 201
    state = response.json()
    assert state["stories"][0]["status"] == "active"
    assert state["round"]["story_id"] == state["stories"][0]["id"]


def test_guest_cannot_add_a_story(client, host_and_room):
    _, room = host_and_room
    code = room["room"]["code"]
    guest = join_guest(client, code)
    response = client.post(
        f"/api/rooms/{code}/stories",
        json={"title": "Sneaky story"},
        headers=auth_headers(guest["access_token"]),
    )
    assert response.status_code == 403


def test_host_activates_a_second_story(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "First"}, headers=headers)
    second = client.post(
        f"/api/rooms/{code}/stories", json={"title": "Second"}, headers=headers
    ).json()
    second_id = second["stories"][1]["id"]
    state = client.post(f"/api/rooms/{code}/stories/{second_id}/activate", headers=headers).json()
    statuses = {s["title"]: s["status"] for s in state["stories"]}
    assert statuses["Second"] == "active"
    assert statuses["First"] == "done"


def test_guest_token_from_another_room_is_rejected(client, host_and_room):
    host, room = host_and_room
    guest = join_guest(client, room["room"]["code"])
    other = make_room(client, host["access_token"])
    other_code = other["room"]["code"]
    guest_headers = auth_headers(guest["access_token"])

    read = client.get(f"/api/rooms/{other_code}", headers=guest_headers)
    assert read.status_code == 403

    vote = client.post(f"/api/rooms/{other_code}/vote", json={"value": "5"}, headers=guest_headers)
    assert vote.status_code == 403

    own = client.get(f"/api/rooms/{room['room']['code']}", headers=guest_headers)
    assert own.status_code == 200


def test_same_name_guests_are_separate_identities(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "Story"}, headers=headers)

    first = join_guest(client, code, name="Sam")
    second = join_guest(client, code, name="Sam")
    assert first["access_token"] != second["access_token"]

    client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "3"},
        headers=auth_headers(first["access_token"]),
    )
    state = client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "8"},
        headers=auth_headers(second["access_token"]),
    ).json()
    assert state["round"]["vote_count"] == 2


def test_room_state_needs_a_token(client, host_and_room):
    _, room = host_and_room
    response = client.get(f"/api/rooms/{room['room']['code']}")
    assert response.status_code == 401


def test_second_room_gets_a_different_code(client):
    host = register_host(client)
    first = make_room(client, host["access_token"])
    second = make_room(client, host["access_token"])
    assert first["room"]["code"] != second["room"]["code"]
