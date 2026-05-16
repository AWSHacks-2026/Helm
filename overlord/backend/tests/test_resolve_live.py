import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _mock_env():
    os.environ["OVERLORD_MOCK_BEDROCK"] = "1"


def test_post_resolve_live_returns_conflict_id():
    body = {
        "session_id": "sess_live_1",
        "file_path": "src/user.py",
        "agent_a": {"agent_id": "a1", "intent": "cache", "code": "def get_user(): ..."},
        "agent_b": {"agent_id": "a2", "intent": "types", "code": "def get_user(x: str): ..."},
    }
    response = client.post("/resolve", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["conflict_id"]
    assert data["status"] == "pending_approval"
    assert data["resolution"]["conflict_type"] == "merge_conflict"
    assert data["file_path"] == "src/user.py"


@patch("routes.resolve.arbitrate")
def test_resolve_live_passes_session_id_to_arbitrate(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "ok",
        "resolved_code": "def get_user(): pass",
        "tokens_saved_estimate": "~1",
    }

    body = {
        "session_id": "sess_live_99",
        "file_path": "src/user.py",
        "agent_a": {"agent_id": "a1", "intent": "cache", "code": "def get_user(): ..."},
        "agent_b": {"agent_id": "a2", "intent": "types", "code": "def get_user(x: str): ..."},
    }
    response = client.post("/resolve", json=body)
    assert response.status_code == 200

    _, kwargs = mock_arbitrate.call_args
    assert kwargs.get("session_id") == "sess_live_99"
