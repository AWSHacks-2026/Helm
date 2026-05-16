import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_mock_bedrock():
    os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
    yield


def test_get_scenarios_lists_merge_conflict():
    response = client.get("/scenarios")
    assert response.status_code == 200
    assert "merge_conflict" in response.json()


def test_resolve_merge_conflict_with_mock_bedrock_e2e():
    response = client.post("/resolve/demo/merge_conflict")
    assert response.status_code == 200
    body = response.json()
    assert body["resolution"]["conflict_type"] == "merge_conflict"
    assert "get_user" in body["resolution"]["resolved_code"]


@patch("routes.resolve.arbitrate")
def test_resolve_demo_returns_api_contract(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "Merged cache and types.",
        "resolved_code": "def get_user(user_id: str) -> User: ...",
        "tokens_saved_estimate": "~2400",
    }

    response = client.post("/resolve/demo/merge_conflict")
    assert response.status_code == 200
    body = response.json()
    assert body["agent_a"]["intent"]
    assert body["resolution"]["resolved_code"]
    mock_arbitrate.assert_called_once()
