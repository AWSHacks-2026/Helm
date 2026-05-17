import json

import pytest

from ws.hub import ConnectionManager


@pytest.mark.asyncio
async def test_broadcast_reaches_subscribed_session():
    hub = ConnectionManager()
    received: list[str] = []

    async def fake_send(data: str) -> None:
        received.append(data)

    hub.subscribe("sess_1", fake_send)
    await hub.broadcast("sess_1", {"type": "conflict_created", "conflict_id": "c1"})
    assert "conflict_created" in received[0]


@pytest.mark.asyncio
async def test_broadcast_serializes_typed_orchestration_event():
    hub = ConnectionManager()
    received: list[str] = []

    async def fake_send(data: str) -> None:
        received.append(data)

    event = {
        "event_type": "intent_declared",
        "payload": {
            "session_id": "sess_1",
            "agent_id": "agent_a",
            "file_path": "src/user.py",
            "intent": "Add caching",
        },
    }
    hub.subscribe("sess_1", fake_send)
    await hub.broadcast("sess_1", {"type": "intent_declared", "event": event})

    assert json.loads(received[0]) == {"type": "intent_declared", "event": event}
