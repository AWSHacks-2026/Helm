import os

os.environ["HELM_MOCK_BEDROCK"] = "1"

from agents.intent_harness import run_intent_benchmark


def test_intent_benchmark_detects_conflict_and_unifies():
    result = run_intent_benchmark("intent_conflict")
    c = result["comparison"]
    o = result["helm"]

    assert c["helm_stops_conflict"] is True
    assert o["conflict_detected_before_code"] is True
    assert o["unified_intent"]
    assert "performance" in o["unified_intent"].lower() or "native" in o["unified_intent"].lower()
    assert c["baseline_agents_proceeding"] == 2
    assert c["helm_agents_proceeding"] == 1
    assert c["helm_beats_cost"] is True
    assert c["cost_savings_pct"] > 0


def test_intent_resolution_contract_fields():
    raw = run_intent_benchmark()["helm"]["resolution"]
    assert raw["conflict_type"] == "intent_conflict"
    assert raw["compatibility"] == "conflict"
    assert raw["priority_order"]
    assert raw["agent_updates"]["agent_a"]
    assert raw["agent_updates"]["agent_b"]
