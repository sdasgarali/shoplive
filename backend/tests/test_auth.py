"""Auth flow tests: register -> login -> me, with error cases."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Use a throwaway SQLite file per test session.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402  (import after env is set)

init_db()  # TestClient doesn't run the lifespan; create tables explicitly
client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_me():
    r = client.post(
        "/auth/register",
        json={"email": "buyer@example.com", "username": "buyer1", "password": "supersecret"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    assert token

    # duplicate registration is rejected
    r2 = client.post(
        "/auth/register",
        json={"email": "buyer@example.com", "username": "buyer1", "password": "supersecret"},
    )
    assert r2.status_code == 409

    # login via OAuth2 form (email in the username field)
    r3 = client.post("/auth/login", data={"username": "buyer@example.com", "password": "supersecret"})
    assert r3.status_code == 200, r3.text
    token = r3.json()["access_token"]

    # /me with the token
    r4 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 200
    body = r4.json()
    assert body["email"] == "buyer@example.com"
    assert body["is_seller"] is False


def test_login_wrong_password():
    client.post(
        "/auth/register",
        json={"email": "s@example.com", "username": "seller1", "password": "supersecret", "is_seller": True},
    )
    r = client.post("/auth/login", data={"username": "s@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_auth():
    assert client.get("/auth/me").status_code == 401
