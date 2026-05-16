from agents.scenarios import SCENARIOS


def test_merge_conflict_scenario_exists_with_required_keys():
    scenario = SCENARIOS["merge_conflict"]
    assert "agent_a" in scenario
    assert "agent_b" in scenario
    assert scenario["agent_a"]["intent"]
    assert "caching" in scenario["agent_a"]["intent"].lower()
    assert "get_user" in scenario["agent_a"]["code"]
    assert "get_user" in scenario["agent_b"]["code"]
