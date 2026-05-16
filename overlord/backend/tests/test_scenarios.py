from agents.scenarios import SCENARIOS, SCENARIO_META


def test_merge_conflict_scenario_exists_with_required_keys():
    scenario = SCENARIOS["merge_conflict"]
    assert "agent_a" in scenario
    assert "agent_b" in scenario
    assert scenario["agent_a"]["intent"]
    assert "caching" in scenario["agent_a"]["intent"].lower()
    assert "get_user" in scenario["agent_a"]["code"]
    assert "get_user" in scenario["agent_b"]["code"]


def test_all_three_demo_scenarios_registered():
    assert set(SCENARIOS.keys()) >= {
        "merge_conflict",
        "intent_conflict",
        "guardrail_prevention",
    }


def test_scenario_meta_kinds():
    assert SCENARIO_META["merge_conflict"]["kind"] == "merge"
    assert SCENARIO_META["intent_conflict"]["kind"] == "intent"
    assert SCENARIO_META["guardrail_prevention"]["kind"] == "guardrail"


def test_intent_conflict_scenario_from_prd():
    s = SCENARIOS["intent_conflict"]
    assert "performance" in s["agent_a"]["intent"].lower()
    assert "dependenc" in s["agent_b"]["intent"].lower()
    assert s["agent_a"]["code"]
    assert s["agent_b"]["code"]
