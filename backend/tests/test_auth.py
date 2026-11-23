"""Registration, sign in and credential safety."""

from conftest import auth_headers, make_room, register_host


def test_register_returns_a_token(client):
    body = register_host(client)
    assert body["access_token"]
    assert body["name"] == "Harriet Host"


def test_register_rejects_a_duplicate_email(client):
    register_host(client)
    response = client.post(
        "/api/auth/register",
        json={"email": "host@example.com", "name": "Second", "password": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_register_rejects_a_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "name": "New", "password": "short"},
    )
    assert response.status_code == 422


def test_login_with_correct_password(client):
    register_host(client)
    response = client.post(
        "/api/auth/login", json={"email": "host@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_is_refused(client):
    register_host(client)
    response = client.post(
        "/api/auth/login", json={"email": "host@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_room_creation_needs_a_host_token(client):
    response = client.post("/api/rooms", json={"name": "Nope"})
    assert response.status_code == 401


def test_password_is_stored_hashed(client):
    from app import repositories
    from app.database import SessionLocal

    register_host(client)
    db = SessionLocal()
    user = repositories.get_user_by_email(db, "host@example.com")
    assert user is not None
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")
    db.close()


def test_host_can_create_a_room(client):
    host = register_host(client)
    room = make_room(client, host["access_token"])
    assert len(room["room"]["code"]) == 6
    unused = auth_headers(host["access_token"])
    assert unused["Authorization"].startswith("Bearer ")
