import json
import os
import shutil

from fastapi.testclient import TestClient

os.environ["HELM_MOCK_BEDROCK"] = "1"

from bedrock import knowledge_base  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def test_intent_recorded_in_history(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_PATH", str(tmp_path / "session.json"))
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "true")
    session_id = "sess_intent_hist"
    received: list[str] = []

    async def fake_send(data: str) -> None:
        received.append(data)

    app.state.ws_hub.subscribe(session_id, fake_send)

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
    intent_events = [
        event for event in events if event["event_type"] == "intent_declared"
    ]
    assert len(intent_events) == 1
    assert intent_events[0]["agent_id"] == "agent_a"
    assert intent_events[0]["payload"] == {
        "intent": "Add caching",
        "file_path": "src/user.py",
    }
    assert json.loads(received[0]) == {
        "type": "intent_declared",
        "event": {
            "event_type": "intent_declared",
            "payload": {
                "session_id": session_id,
                "agent_id": "agent_a",
                "file_path": "src/user.py",
                "intent": "Add caching",
            },
        },
    }
    shutil.rmtree(tmp_path)


def test_history_returns_ordinary_action_events(monkeypatch):
    monkeypatch.setattr(
        knowledge_base,
        "list_history",
        lambda session_id: [
            {
                "event_id": "event-1",
                "session_id": session_id,
                "timestamp": "2026-05-16T18:06:00.000Z",
                "event_type": "action",
                "agent_id": "agent_a",
                "payload": {"action": "write", "file_path": "src/user.py"},
            }
        ],
    )

    history = client.get("/history", params={"session_id": "sess_action_hist"})

    assert history.status_code == 200
    assert history.json() == [
        {
            "event_id": "event-1",
            "session_id": "sess_action_hist",
            "timestamp": "2026-05-16T18:06:00.000Z",
            "event_type": "action",
            "agent_id": "agent_a",
            "payload": {"action": "write", "file_path": "src/user.py"},
        }
    ]


def test_decision_history_preserves_resolved_and_approved_events(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_PATH", str(tmp_path / "session.json"))
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "true")
    session_id = "sess_decision_hist"

    knowledge_base.append_event(
        session_id,
        {
            "event_type": "conflict_resolved",
            "payload": {
                "conflict_id": "conflict-1",
                "file_path": "src/user.py",
                "resolution": {"conflict_type": "merge_conflict"},
            },
        },
    )
    knowledge_base.append_event(
        session_id,
        {
            "event_type": "conflict_approved",
            "payload": {
                "conflict_id": "conflict-1",
                "status": "approved",
            },
        },
    )

    events = client.get("/history", params={"session_id": session_id}).json()

    assert [event["event_type"] for event in events] == [
        "conflict_approved",
        "conflict_resolved",
    ]
    assert events[0]["payload"] == {
        "conflict_id": "conflict-1",
        "status": "approved",
    }
    assert events[1]["payload"] == {
        "conflict_id": "conflict-1",
        "file_path": "src/user.py",
        "resolution": {"conflict_type": "merge_conflict"},
    }
