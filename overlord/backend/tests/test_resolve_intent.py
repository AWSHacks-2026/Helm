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


def test_get_scenarios_includes_all_demo_scenarios():
    response = client.get("/scenarios")

    assert response.status_code == 200
    assert {
        "merge_conflict",
        "intent_conflict",
        "dependency_conflict",
        "guardrail_prevention",
    }.issubset(response.json())


def test_resolve_intent_conflict_returns_contract_payload():
    response = client.post("/resolve/intent_conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_a"]["intent"].startswith("I am optimizing this module")
    assert body["agent_b"]["intent"].startswith("I am refactoring this module")
    assert body["resolution"]["conflict_type"] == "intent_conflict"
    assert body["resolution"]["compatibility"] == "conflict"
    assert body["resolution"]["unified_intent"] == (
        "Optimize for performance where measurable, but prefer native Python "
        "implementations unless a dependency saves at least 20% latency on the "
        "demo path."
    )
    assert body["resolution"]["tokens_saved_estimate"] == "2400 tokens saved (75%)"
    assert body["resolution"]["priority_order"] == [
        "preserve deployability and low dependency count",
        "improve latency with standard-library techniques first",
        "allow a new dependency only with benchmark evidence",
    ]
    assert body["resolution"]["agent_updates"] == {
        "agent_a": "Benchmark stdlib json plus functools.lru_cache before proposing orjson.",
        "agent_b": (
            "Keep dependency removals unless Agent A provides benchmark evidence for "
            "a targeted exception."
        ),
    }


def test_resolve_dependency_conflict_returns_contract_payload():
    response = client.post("/resolve/dependency_conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["agent_a"]["intent"]
    assert body["agent_b"]["intent"]
    assert body["resolution"]["conflict_type"] == "dependency_conflict"
    assert "shared demo catalog" in body["resolution"]["reasoning"]
    assert "Redis" in body["resolution"]["resolved_code"]
    assert body["resolution"]["tokens_saved_estimate"] == "0 tokens saved (0%)"


@patch("main.arbitrate")
def test_resolve_merge_conflict_still_uses_arbitrate(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "Merged cache and types.",
        "resolved_code": "def get_user(user_id: str) -> User: ...",
        "tokens_saved_estimate": "~2400",
    }

    response = client.post("/resolve/merge_conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["resolution"]["conflict_type"] == "merge_conflict"
    assert body["resolution"]["resolved_code"]
    mock_arbitrate.assert_called_once()


@patch("main.arbitrate")
def test_resolve_merge_conflict_omits_feature_2_only_fields(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "Merged cache and types.",
        "resolved_code": "def get_user(user_id: str) -> User: ...",
        "tokens_saved_estimate": "~2400",
    }

    response = client.post("/resolve/merge_conflict")

    assert response.status_code == 200
    resolution = response.json()["resolution"]
    assert "compatibility" not in resolution
    assert "unified_intent" not in resolution
    assert "priority_order" not in resolution
    assert "agent_updates" not in resolution


def test_resolve_unknown_scenario_returns_404_detail():
    response = client.post("/resolve/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Scenario not found"}


@patch("main.kb.get_history")
def test_history_route_uses_knowledge_base_history(mock_get_history):
    mock_get_history.return_value = [{"id": "record-1"}]

    response = client.get("/history?limit=7")

    assert response.status_code == 200
    assert response.json() == [{"id": "record-1"}]
    mock_get_history.assert_called_once_with(limit=7)
