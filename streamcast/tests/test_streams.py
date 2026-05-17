from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.streams.live import register_routes


def _client() -> TestClient:
    app = FastAPI()
    register_routes(app)
    return TestClient(app)


def test_create_and_get_stream():
    client = _client()
    created = client.post(
        "/streams",
        json={"title": "Late Night Code", "broadcaster": "alice"},
    )
    assert created.status_code == 201
    stream_id = created.json()["id"]
    got = client.get(f"/streams/{stream_id}")
    assert got.status_code == 200
    assert got.json()["title"] == "Late Night Code"


def test_go_live():
    client = _client()
    stream_id = client.post(
        "/streams",
        json={"title": "Speedrun", "broadcaster": "bob"},
    ).json()["id"]
    live = client.post(f"/streams/{stream_id}/live")
    assert live.status_code == 200
    assert live.json()["is_live"] is True


def test_unknown_stream_404():
    client = _client()
    assert client.get("/streams/missing-id").status_code == 404
