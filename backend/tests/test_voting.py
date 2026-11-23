"""Voting, hidden values, reveal maths and reset."""

from conftest import auth_headers


def setup_room_with_story(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    headers = auth_headers(host["access_token"])
    client.post(f"/api/rooms/{code}/stories", json={"title": "Story one"}, headers=headers)
    guest = client.post("/api/rooms/join", json={"code": code, "name": "Gus Guest"}).json()
    return host, code, headers, guest


def test_votes_stay_hidden_until_reveal(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    state = client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "8"},
        headers=auth_headers(guest["access_token"]),
    ).json()
    assert state["round"]["vote_count"] == 1
    assert state["round"]["results"] is None
    assert state["round"]["revealed"] is False


def test_reveal_shows_votes_average_and_agreement(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    client.post(f"/api/rooms/{code}/vote", json={"value": "5"}, headers=headers)
    client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "5"},
        headers=auth_headers(guest["access_token"]),
    )
    state = client.post(f"/api/rooms/{code}/reveal", headers=headers).json()
    results = state["round"]["results"]
    assert results["average"] == 5.0
    assert results["agreement"] == 100
    values = {v["name"]: v["value"] for v in results["votes"]}
    assert values["Gus Guest"] == "5"


def test_guest_cannot_reveal(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    response = client.post(f"/api/rooms/{code}/reveal", headers=auth_headers(guest["access_token"]))
    assert response.status_code == 403


def test_invalid_card_is_rejected(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    response = client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "99"},
        headers=auth_headers(guest["access_token"]),
    )
    assert response.status_code == 400


def test_voting_without_an_active_story_fails(client, host_and_room):
    host, room = host_and_room
    code = room["room"]["code"]
    response = client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "3"},
        headers=auth_headers(host["access_token"]),
    )
    assert response.status_code == 400


def test_reset_clears_votes_and_hides_results(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    client.post(f"/api/rooms/{code}/vote", json={"value": "3"}, headers=headers)
    client.post(f"/api/rooms/{code}/reveal", headers=headers)
    state = client.post(f"/api/rooms/{code}/reset", headers=headers).json()
    assert state["round"]["vote_count"] == 0
    assert state["round"]["revealed"] is False


def test_changing_a_vote_replaces_it(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    guest_headers = auth_headers(guest["access_token"])
    client.post(f"/api/rooms/{code}/vote", json={"value": "3"}, headers=guest_headers)
    state = client.post(
        f"/api/rooms/{code}/vote", json={"value": "13"}, headers=guest_headers
    ).json()
    assert state["round"]["vote_count"] == 1


def test_question_and_pass_cards_do_not_change_the_average(client, host_and_room):
    host, code, headers, guest = setup_room_with_story(client, host_and_room)
    client.post(f"/api/rooms/{code}/vote", json={"value": "?"}, headers=headers)
    client.post(
        f"/api/rooms/{code}/vote",
        json={"value": "8"},
        headers=auth_headers(guest["access_token"]),
    )
    state = client.post(f"/api/rooms/{code}/reveal", headers=headers).json()
    assert state["round"]["results"]["average"] == 8.0
