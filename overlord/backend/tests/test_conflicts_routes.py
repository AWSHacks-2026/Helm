import os

from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402

client = TestClient(app)


def _create_conflict(session_id: str = "sess_conflicts") -> str:
    body = {
        "session_id": session_id,
        "file_path": "src/user.py",
        "agent_a": {"agent_id": "a1", "intent": "cache", "code": "a"},
        "agent_b": {"agent_id": "a2", "intent": "types", "code": "b"},
    }
    response = client.post("/resolve", json=body)
    assert response.status_code == 200
    return response.json()["conflict_id"]


def test_list_conflicts_after_resolve():
    conflict_id = _create_conflict()
    response = client.get("/conflicts", params={"session_id": "sess_conflicts"})
    assert response.status_code == 200
    data = response.json()
    assert any(item["conflict_id"] == conflict_id for item in data)


def test_approve_conflict():
    conflict_id = _create_conflict("sess_approve")
    response = client.post(
        f"/conflicts/{conflict_id}/approve",
        json={"approved": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_resolve_unknown_scenario_returns_404():
    response = client.post("/resolve/demo/does_not_exist")
    assert response.status_code == 404
