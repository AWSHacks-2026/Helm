import os

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
