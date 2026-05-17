import os

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"
os.environ["OVERLORD_USE_LOCAL_MEMORY"] = "true"
os.environ["OVERLORD_USE_LOCAL_POLICY"] = "true"

from fastapi.testclient import TestClient

from agents.guardrail_harness import run_guardrail_benchmark
from main import app  # noqa: E402

client = TestClient(app)


def test_guardrail_benchmark_blocks_destructive_action():
    result = run_guardrail_benchmark()
    c = result["comparison"]
    o = result["overlord"]

    assert c["baseline_executed"] is True
    assert c["overlord_executed"] is False
    assert c["overlord_blocked_action"] is True
    assert o["preflight_allowed"] is False
    assert o["blocked_rule"] in {"file_overlap", "reverses_recent_decision", "intent_contradiction"}
    assert o["resolution"] is not None
    assert o["resolution"].get("verdict") == "modify" or o.get("verdict") == "modify"
    assert o.get("resolution_tier") in {"haiku", "sonnet"}


def test_guardrail_check_api_demo():
    response = client.post("/guardrail/check")
    assert response.status_code == 200
    body = response.json()
    assert body["preflight"]["allowed"] is False
    assert body["executed"] is False
    assert body["resolution"]["conflict_type"] == "proactive_guardrail"


def test_guardrail_preflight_blocks_file_overlap():
    from bedrock import guardrails, knowledge_base as kb

    session = "test-guardrail-overlap"
    kb.log_action(
        "agent_a",
        "add_file",
        "utils/cache.py",
        "Added cache",
        session_id=session,
    )
    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility",
    }
    preflight = guardrails.preflight_check(proposed, session_id=session)
    assert preflight.allowed is False
    assert preflight.rule is not None
