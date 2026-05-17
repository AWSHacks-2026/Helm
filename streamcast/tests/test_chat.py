from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.chat.room import register_routes


def _client() -> TestClient:
    app = FastAPI()
    register_routes(app)
    return TestClient(app)


def test_post_and_list_messages():
    client = _client()
    stream_id = "live-42"
    post = client.post(
        f"/chat/{stream_id}/messages",
        json={"author": "viewer1", "body": "hello chat"},
    )
    assert post.status_code == 201
    listed = client.get(f"/chat/{stream_id}/messages")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["body"] == "hello chat"
