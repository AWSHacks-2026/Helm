from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_gratitude_endpoint_returns_ledger_shape():
    response = client.get("/gratitude", params={"session_id": "mergeai-hackathon-demo"})
    assert response.status_code == 200
    body = response.json()
    assert body["tokens_saved_display"]
    assert isinstance(body["timeline"], list)


def test_gratitude_falls_back_when_agentcore_raises(monkeypatch):
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "false")
    monkeypatch.setenv("AGENTCORE_MEMORY_ID", "missing-memory-id")

    class BrokenClient:
        def list_events(self, **_kwargs):
            raise RuntimeError("ResourceNotFoundException: Memory not found")

    monkeypatch.setattr(
        "bedrock_agentcore.memory.MemoryClient",
        BrokenClient,
    )

    response = client.get("/gratitude", params={"session_id": "mergeai-hackathon-demo"})
    assert response.status_code == 200


def test_append_event_falls_back_to_local_when_agentcore_write_fails(monkeypatch):
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "false")
    monkeypatch.setenv("AGENTCORE_MEMORY_ID", "missing-memory-id")

    class BrokenClient:
        def create_event(self, **_kwargs):
            raise RuntimeError("ResourceNotFoundException: Memory not found")

    monkeypatch.setattr(
        "bedrock_agentcore.memory.MemoryClient",
        BrokenClient,
    )

    from bedrock.knowledge_base import append_event

    append_event(
        "write-fallback-session",
        {
            "event_type": "guardrail_blocked",
            "payload": {
                "agent_id": "agent_b",
                "file_path": "auth.py",
                "message": "blocked",
            },
        },
    )

    gratitude = client.get("/gratitude", params={"session_id": "write-fallback-session"})
    assert gratitude.status_code == 200
    assert gratitude.json()["guardrails_blocked"] >= 1


def test_intent_aligned_roundtrip_counts_tokens():
    session_id = "ledger-intent-aligned-tokens"
    response = client.post(
        "/history/event",
        json={
            "session_id": session_id,
            "event_type": "intent_aligned",
            "payload": {
                "tokens_saved_estimate": "~1,080",
                "inference_tier": "haiku",
            },
        },
    )
    assert response.status_code == 200

    gratitude = client.get("/gratitude", params={"session_id": session_id})
    body = gratitude.json()
    assert body["intents_aligned"] >= 1
    assert body["tokens_saved_total"] >= 1080
    assert "1,080" in body["tokens_saved_display"]


def test_history_event_records_guardrail_for_ledger():
    session_id = "ledger-test-session-gratitude"
    response = client.post(
        "/history/event",
        json={
            "session_id": session_id,
            "event_type": "guardrail_blocked",
            "payload": {
                "agent_id": "agent_b",
                "file_path": "backend/app/routers/auth.py",
                "message": "blocked destructive edit",
            },
        },
    )
    assert response.status_code == 200

    gratitude = client.get("/gratitude", params={"session_id": session_id})
    assert gratitude.status_code == 200
    assert gratitude.json()["guardrails_blocked"] >= 1
