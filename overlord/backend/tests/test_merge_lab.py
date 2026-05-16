import os

import pytest
from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
os.environ["OVERLORD_USE_LOCAL_MEMORY"] = "true"
os.environ["OVERLORD_USE_LOCAL_POLICY"] = "true"

from main import app  # noqa: E402

client = TestClient(app)


def test_list_merge_scenarios():
    response = client.get("/merge/scenarios")
    assert response.status_code == 200
    names = {s["name"] for s in response.json()}
    assert "merge_conflict" in names
    assert "merge_rate_limit" in names
    assert len(names) >= 4


def test_compare_merge_conflict_overlord_beats_naive():
    response = client.post("/merge/compare/merge_conflict")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["overlord_passed"] is True
    assert body["summary"]["overlord_beats_naive"] is True
    assert body["summary"]["score_delta"] > 0


def test_compare_unknown_scenario_404():
    response = client.post("/merge/compare/not_a_scenario")
    assert response.status_code == 404


def test_merge_evaluator_syntax_fails_on_conflict_markers():
    from agents.merge_evaluator import evaluate_merge_resolution
    from agents.naive_merge import conflict_markers

    scenario = {
        "agent_a": {"code": "def f():\n    return 1"},
        "agent_b": {"code": "def f():\n    return 2"},
    }
    naive = conflict_markers(scenario["agent_a"], scenario["agent_b"])
    result = evaluate_merge_resolution(
        naive["resolved_code"],
        scenario["agent_a"]["code"],
        scenario["agent_b"]["code"],
        {"must_include": ["f"], "must_not_equal_agent": True},
    )
    assert result["passed"] is False
    assert result["checks"]["syntax_valid"] is False
