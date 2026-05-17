import os

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
os.environ["OVERLORD_USE_LOCAL_MEMORY"] = "true"
os.environ["OVERLORD_USE_LOCAL_POLICY"] = "true"

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_second_intent_declare_returns_alignment(monkeypatch):
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")
    session = "intent-align-test"
    client.post(
        "/intents",
        json={
            "session_id": session,
            "agent_id": "agent_a",
            "file_path": "src/x.py",
            "intent": "maximum performance caching",
        },
    )
    response = client.post(
        "/intents",
        json={
            "session_id": session,
            "agent_id": "agent_b",
            "file_path": "src/x.py",
            "intent": "minimize external dependencies",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["overlap_detected"] is True
    assert body["alignment"]["unified_intent"]
