"""Shared fixtures. Tests run on SQLite with the in memory event bus."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_pointgoblin.db"
os.environ["EVENT_BUS"] = "memory"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret-for-local-tests-0123456789"

import pytest
from fastapi.testclient import TestClient

from app import models
from app.database import engine, init_db


@pytest.fixture(autouse=True)
def clean_db():
    models.Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    models.Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(__import__("app.main", fromlist=["app"]).app)


def register_host(client: TestClient, email: str = "host@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Harriet Host", "password": "password123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_room(client: TestClient, token: str) -> dict:
    response = client.post(
        "/api/rooms", json={"name": "Sprint 24 planning"}, headers=auth_headers(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def host_and_room(client: TestClient) -> tuple[dict, dict]:
    host = register_host(client)
    room = make_room(client, host["access_token"])
    return host, room
