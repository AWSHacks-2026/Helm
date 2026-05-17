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
