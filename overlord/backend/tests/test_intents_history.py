import os
import shutil

from fastapi.testclient import TestClient

from bedrock import knowledge_base

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402

client = TestClient(app)


def test_intent_recorded_in_history(tmp_path, monkeypatch):
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(tmp_path / "session.json"))
    monkeypatch.setenv("OVERLORD_USE_LOCAL_KB", "true")
    session_id = "sess_intent_hist"

    response = client.post(
        "/intents",
        json={
            "session_id": session_id,
            "agent_id": "agent_a",
            "file_path": "src/user.py",
            "intent": "Add caching",
        },
    )
    assert response.status_code == 200
    assert response.json()["recorded"] is True

    history = client.get("/history", params={"session_id": session_id})
    assert history.status_code == 200
    events = history.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "intent_declared"
    shutil.rmtree(tmp_path)
