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


def test_sec1_placeholders_still_work_in_dev_mode():
    settings = Settings(
        jwt_secret="replace-with-a-long-random-value",
        environment="dev",
    )
    assert settings.environment == "dev"
