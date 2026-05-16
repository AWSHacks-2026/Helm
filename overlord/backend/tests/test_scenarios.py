from agents.scenarios import SCENARIOS, get_scenario, get_scenario_names


def test_merge_conflict_scenario_exists_with_required_keys():
    scenario = SCENARIOS["merge_conflict"]
    assert "agent_a" in scenario
    assert "agent_b" in scenario
    assert scenario["agent_a"]["intent"]
    assert "caching" in scenario["agent_a"]["intent"].lower()
    assert "get_user" in scenario["agent_a"]["code"]
    assert "get_user" in scenario["agent_b"]["code"]


def test_guardrail_prevention_scenario_still_exists():
    scenario = SCENARIOS["guardrail_prevention"]
    assert "agent_a" in scenario
    assert "agent_b" in scenario


def test_intent_conflict_scenario_contains_performance_vs_minimalism():
    scenario = SCENARIOS["intent_conflict"]

    assert scenario["title"] == "Performance vs. Minimalism"
    assert scenario["agent_a"]["intent"] == (
        "I am optimizing this module for maximum performance, even if it means "
        "adding specialized caching and parsing dependencies."
    )
    assert (
        "Agent A has not written code yet"
        in scenario["agent_a"]["code"]
    )
    assert "orjson" in scenario["agent_a"]["code"]
    assert "cache hot-path parsed payloads" in scenario["agent_a"]["code"]
    assert "orjson" in scenario["agent_a"]["proposed_action"]
    assert "LRU cache" in scenario["agent_a"]["proposed_action"]

    assert scenario["agent_b"]["intent"] == (
        "I am refactoring this module to minimize external dependencies and keep "
        "the deployment artifact small."
    )
    assert (
        "Agent B has not written code yet"
        in scenario["agent_b"]["code"]
    )
    assert "standard library json" in scenario["agent_b"]["code"]
    assert "standard library json" in scenario["agent_b"]["proposed_action"]

    assert scenario["history"] == [
        {
            "agent": "agent_a",
            "decision": "Prioritized low-latency request handling in the API layer.",
        },
        {
            "agent": "agent_b",
            "decision": "Reduced image size by removing unused transitive dependencies.",
        },
    ]


def test_duplicate_work_scenario_contains_overlapping_auth_intents():
    scenario = SCENARIOS["duplicate_work"]

    assert scenario["title"] == "Duplicate User Authentication Work"
    assert scenario["agent_a"]["intent"] == (
        "I am implementing JWT-based user authentication for the API login flow."
    )
    assert scenario["agent_b"]["intent"] == (
        "I am building user sign-in and session validation for the same API."
    )
    assert "login" in scenario["agent_a"]["code"]
    assert "session validation" in scenario["agent_b"]["code"]
    assert "authentication" in scenario["agent_a"]["proposed_action"]
    assert "sign-in" in scenario["agent_b"]["proposed_action"]
    assert "duplicate_work" in get_scenario_names()


def test_get_scenario_returns_deep_copy():
    scenario = get_scenario("intent_conflict")

    scenario["agent_a"]["intent"] = "mutated"
    scenario["history"][0]["decision"] = "mutated"

    assert SCENARIOS["intent_conflict"]["agent_a"]["intent"] == (
        "I am optimizing this module for maximum performance, even if it means "
        "adding specialized caching and parsing dependencies."
    )
    assert (
        SCENARIOS["intent_conflict"]["history"][0]["decision"]
        == "Prioritized low-latency request handling in the API layer."
    )


def test_get_scenario_names_includes_existing_and_prd_scenarios():
    names = get_scenario_names()

    assert names.index("merge_conflict") < names.index("intent_conflict")
    assert {
        "merge_conflict",
        "intent_conflict",
        "dependency_conflict",
        "guardrail_prevention",
    }.issubset(names)
