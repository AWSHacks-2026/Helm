import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from bedrock import agentcore_memory as mem
from bedrock.guardrails import check_action
from main import app


def test_check_action_uses_memory_when_cloud(monkeypatch, tmp_path):
    monkeypatch.setenv("OVERLORD_USE_LOCAL_MEMORY", "true")
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(tmp_path / "session.json"))
    from bedrock import agentcore_memory as mem

    sid = "shared-sess"
    mem.log_intent(sid, "agent_a", "work on file", file_path="f.py")
    store = MagicMock()
    store.agents_on_file.return_value = []

    result = check_action(
        session_id=sid,
        agent_id="agent_b",
        file_path="f.py",
        action="write",
        proposed_code="x",
        session_store=store,
    )
    assert result.allowed is False
    assert "agent_a" in result.reason


def test_guardrails_check_records_and_broadcasts_blocked_event(monkeypatch, tmp_path):
    monkeypatch.setenv("OVERLORD_USE_LOCAL_MEMORY", "true")
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(tmp_path / "session.json"))
    session_id = "guardrail-route-sess"
    received: list[str] = []

    async def fake_send(data: str) -> None:
        received.append(data)

    mem.log_intent(session_id, "agent_a", "Own cache module", file_path="src/cache.py")
    app.state.ws_hub.subscribe(session_id, fake_send)

    response = TestClient(app).post(
        "/guardrails/check",
        json={
            "session_id": session_id,
            "agent_id": "agent_b",
            "file_path": "src/cache.py",
            "action": "write",
            "proposed_code": "cache = {}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["route_to_overlord"] is True
    assert "agent_a" in body["reason"]

    history = TestClient(app).get("/history", params={"session_id": session_id})
    guardrail_events = [
        event
        for event in history.json()
        if event["event_type"] == "guardrail_blocked"
    ]
    assert len(guardrail_events) == 1
    assert guardrail_events[0]["agent_id"] == "agent_b"
    assert guardrail_events[0]["payload"]["description"] == body["reason"]

    assert json.loads(received[0]) == {
        "type": "guardrail_blocked",
        "event": {
            "event_type": "guardrail_blocked",
            "payload": {
                "session_id": session_id,
                "agent_id": "agent_b",
                "file_path": "src/cache.py",
                "action": "write",
                "proposed_code": "cache = {}",
                "reason": body["reason"],
            },
        },
    }
