import os

os.environ["HELM_MOCK_BEDROCK"] = "1"

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_intent_post_includes_contention_allow_when_alone():
    r = client.post(
        "/intents",
        json={
            "session_id": "gate-test-solo",
            "agent_id": "agent_a",
            "file_path": "app/only.py",
            "intent": "Work on billing module",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["contention"]["gate_tier"] == "allow"
    assert body["contention"]["contention_detected"] is False
