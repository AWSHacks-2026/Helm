from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.player.session import register_routes


def _client() -> TestClient:
    app = FastAPI()
    register_routes(app)
    return TestClient(app)


def test_pause_and_resume():
    client = _client()
    stream_id = "stream-1"
    client.post(f"/player/{stream_id}/pause")
    assert client.get(f"/player/{stream_id}/state").json()["state"] == "paused"
    client.post(f"/player/{stream_id}/resume")
    assert client.get(f"/player/{stream_id}/state").json()["state"] == "playing"


def test_state_before_pause_creates_session():
    client = _client()
    paused = client.post("/player/new-stream/pause")
    assert paused.status_code == 200
    assert paused.json()["state"] == "paused"
