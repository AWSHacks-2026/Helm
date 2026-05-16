from agents.scenarios import get_scenario
from agents.simulator import resolve_intent_conflict


def test_resolve_intent_conflict_prioritizes_native_performance():
    scenario = get_scenario("intent_conflict")

    result = resolve_intent_conflict(
        agent_a=scenario["agent_a"],
        agent_b=scenario["agent_b"],
        history=scenario["history"],
    )

    assert result["conflict_type"] == "intent_conflict"
    assert result["compatibility"] == "conflict"
    assert result["unified_intent"] == (
        "Optimize for performance where measurable, but prefer native Python "
        "implementations unless a dependency saves at least 20% latency on the "
        "demo path."
    )
    assert result["priority_order"] == [
        "preserve deployability and low dependency count",
        "improve latency with standard-library techniques first",
        "allow a new dependency only with benchmark evidence",
    ]
    assert result["tokens_saved_estimate"] == "2400 tokens saved (75%)"


def test_resolve_intent_conflict_returns_actionable_agent_updates():
    scenario = get_scenario("intent_conflict")

    result = resolve_intent_conflict(
        agent_a=scenario["agent_a"],
        agent_b=scenario["agent_b"],
        history=scenario["history"],
    )

    assert result["agent_updates"] == {
        "agent_a": (
            "Benchmark stdlib json plus functools.lru_cache before proposing orjson."
        ),
        "agent_b": (
            "Keep dependency removals unless Agent A provides benchmark evidence for "
            "a targeted exception."
        ),
    }
    assert result["resolved_code"].startswith("Unified directive:")
    assert result["unified_intent"] in result["resolved_code"]
    assert result["agent_updates"]["agent_a"] in result["resolved_code"]
    assert result["agent_updates"]["agent_b"] in result["resolved_code"]


def test_resolve_intent_conflict_formats_history():
    scenario = get_scenario("intent_conflict")

    result = resolve_intent_conflict(
        agent_a=scenario["agent_a"],
        agent_b=scenario["agent_b"],
        history=scenario["history"],
    )

    assert result["history_used"] == [
        "agent_a: Prioritized low-latency request handling in the API layer.",
        "agent_b: Reduced image size by removing unused transitive dependencies.",
    ]


def test_resolve_intent_conflict_returns_fresh_mutable_payloads():
    scenario = get_scenario("intent_conflict")

    result = resolve_intent_conflict(
        agent_a=scenario["agent_a"],
        agent_b=scenario["agent_b"],
        history=scenario["history"],
    )
    result["priority_order"].append("caller mutation")
    result["agent_updates"]["agent_a"] = "caller mutation"

    next_result = resolve_intent_conflict(
        agent_a=scenario["agent_a"],
        agent_b=scenario["agent_b"],
        history=scenario["history"],
    )

    assert next_result["priority_order"] == [
        "preserve deployability and low dependency count",
        "improve latency with standard-library techniques first",
        "allow a new dependency only with benchmark evidence",
    ]
    assert next_result["agent_updates"] == {
        "agent_a": (
            "Benchmark stdlib json plus functools.lru_cache before proposing orjson."
        ),
        "agent_b": (
            "Keep dependency removals unless Agent A provides benchmark evidence for "
            "a targeted exception."
        ),
    }


def test_resolve_intent_conflict_returns_compatible_fallback():
    result = resolve_intent_conflict(
        agent_a={
            "intent": "I am adding validation for incoming request payloads.",
            "code": "# Validate request data before processing.",
            "proposed_action": "Add required field checks with helpful errors.",
        },
        agent_b={
            "intent": "I am improving API documentation for the same payloads.",
            "code": "# Update OpenAPI examples.",
            "proposed_action": "Document accepted request fields and examples.",
        },
        history=[
            {
                "agent": "agent_b",
                "decision": "Documented response examples for client teams.",
            }
        ],
    )

    assert result["conflict_type"] == "intent_conflict"
    assert result["compatibility"] == "compatible"
    assert result["reasoning"]
    assert result["unified_intent"]
    assert result["priority_order"]
    assert set(result["agent_updates"]) == {"agent_a", "agent_b"}
    assert result["resolved_code"].startswith("Unified directive:")
    assert result["tokens_saved_estimate"] == "2400 tokens saved (75%)"
    assert result["history_used"] == [
        "agent_b: Documented response examples for client teams."
    ]
