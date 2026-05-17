import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["HELM_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402


client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_mock_bedrock():
    os.environ["HELM_MOCK_BEDROCK"] = "1"
    yield


def test_scenarios_include_duplicate_work():
    response = client.get("/scenarios")

    assert response.status_code == 200
    assert "duplicate_work" in response.json()


@patch("routes.resolve.detect_duplication")
def test_resolve_duplicate_work_returns_deduplication_contract(mock_detect):
    mock_detect.return_value = {
        "conflict_type": "duplicate_work",
        "duplicate_detected": True,
        "agent_to_continue": "agent_a",
        "agent_to_reassign": "agent_b",
        "suggested_new_task": "Implement audit logging for authentication events.",
        "reasoning": "Both agents are implementing authentication work.",
        "resolved_code": "",
        "tokens_saved_estimate": "~1800",
    }

    response = client.post("/resolve/duplicate_work")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_a"]["intent"].startswith("I am implementing JWT-based")
    assert body["agent_b"]["intent"].startswith("I am building user sign-in")
    assert body["resolution"]["duplicate_detected"] is True
    assert body["resolution"]["agent_to_continue"] == "agent_a"
    assert body["resolution"]["agent_to_reassign"] == "agent_b"
    assert (
        body["resolution"]["suggested_new_task"]
        == "Implement audit logging for authentication events."
    )
    assert body["resolution"]["reasoning"] == (
        "Both agents are implementing authentication work."
    )
    mock_detect.assert_called_once()


def test_resolve_duplicate_work_mock_e2e():
    response = client.post("/resolve/duplicate_work")

    assert response.status_code == 200
    resolution = response.json()["resolution"]
    assert resolution["conflict_type"] == "duplicate_work"
    assert resolution["duplicate_detected"] is True
    assert resolution["agent_to_continue"] == "agent_a"
    assert resolution["agent_to_reassign"] == "agent_b"
    assert "audit logging" in resolution["suggested_new_task"]
    assert "overlapping user authentication" in resolution["reasoning"]
