from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.handlers import register_routes


def test_register_user_returns_token():
    app = FastAPI()
    register_routes(app)
    client = TestClient(app)
    resp = client.post(
        "/auth/register",
        json={"email": "alice@streamcast.test", "password": "secret12"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_after_register():
    app = FastAPI()
    register_routes(app)
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={"email": "bob@streamcast.test", "password": "secret12"},
    )
    resp = client.post(
        "/auth/login",
        json={"email": "bob@streamcast.test", "password": "secret12"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
