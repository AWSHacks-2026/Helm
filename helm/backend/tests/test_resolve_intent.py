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
    response = client.post("/resolve/demo/intent_conflict")

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


def test_resolve_guardrail_scenario_returns_400():
    response = client.post("/resolve/demo/guardrail_prevention")

    assert response.status_code == 400
    assert "guardrail/check" in response.json()["detail"]


def test_resolve_dependency_conflict_returns_contract_payload():
    response = client.post("/resolve/demo/dependency_conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["resolution"]["conflict_type"] == "dependency_conflict"
    assert "Redis" in body["resolution"]["resolved_code"]


@patch("routes.resolve.arbitrate")
def test_resolve_merge_conflict_still_uses_arbitrate(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "Merged cache and types.",
        "resolved_code": "def get_user(user_id: str) -> User: ...",
        "tokens_saved_estimate": "~2400",
    }

    response = client.post("/resolve/demo/merge_conflict")

    assert response.status_code == 200
    assert response.json()["resolution"]["conflict_type"] == "merge_conflict"
    mock_arbitrate.assert_called_once()


@patch("routes.resolve.arbitrate")
def test_resolve_merge_conflict_omits_feature_2_only_fields(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "Merged cache and types.",
        "resolved_code": "def get_user(user_id: str) -> User: ...",
        "tokens_saved_estimate": "~2400",
    }

    response = client.post("/resolve/demo/merge_conflict")

    resolution = response.json()["resolution"]
    assert "compatibility" not in resolution
    assert "unified_intent" not in resolution


def test_resolve_unknown_scenario_returns_404_detail():
    response = client.post("/resolve/demo/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Scenario not found"}


@patch("routes.history.knowledge_base.list_history")
def test_history_route_uses_knowledge_base_history(mock_list_history):
    mock_list_history.return_value = [
        {
            "event_id": "event-1",
            "session_id": "session-1",
            "timestamp": "2026-05-16T00:00:00Z",
            "event_type": "intent_declared",
            "payload": {"agent_id": "agent_a"},
        }
    ]

    response = client.get("/history?session_id=session-1")

    assert response.status_code == 200
    assert response.json()[0]["event_id"] == "event-1"
    mock_list_history.assert_called_once_with("session-1")
