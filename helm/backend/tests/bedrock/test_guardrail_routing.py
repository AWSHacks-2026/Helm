import os

from bedrock.guardrail_routing import (
    count_distinct_files,
    select_guardrail_tier,
    sonnet_min_agents,
)


def test_select_haiku_for_simple_pairwise():
    tier = select_guardrail_tier(
        agent_count=2,
        preflight_rule="reverses_recent_decision",
        kb_context=[{"file_path": "utils/cache.py"}],
        proposed_action={"file_path": "utils/cache.py"},
    )
    assert tier == "haiku"


def test_select_sonnet_for_intent_contradiction_rule():
    tier = select_guardrail_tier(
        agent_count=2,
        preflight_rule="intent_contradiction",
        kb_context=[],
        proposed_action={"file_path": "utils/cache.py"},
    )
    assert tier == "sonnet"


def test_select_sonnet_for_fleet_agent_count():
    tier = select_guardrail_tier(
        agent_count=sonnet_min_agents(),
        preflight_rule="file_overlap",
        kb_context=[],
        proposed_action={"file_path": "a.py"},
    )
    assert tier == "sonnet"


def test_strategy_override_haiku(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_STRATEGY", "haiku")
    tier = select_guardrail_tier(
        agent_count=5,
        preflight_rule="intent_contradiction",
        kb_context=[],
        proposed_action=None,
    )
    assert tier == "haiku"


def test_count_distinct_files_from_kb():
    n = count_distinct_files(
        {"file_path": "utils/cache.py"},
        [{"file_path": "app/auth/handlers.py"}, {"file_path": "utils/cache.py"}],
    )
    assert n == 2


def test_resolve_guardrail_mock_sets_tier(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    from helm import resolve_guardrail

    result = resolve_guardrail(
        {"intent": "a", "code": ""},
        {"intent": "b", "code": ""},
        guardrail_context={
            "proposed_action": {"agent_id": "agent_b", "file_path": "x.py"},
            "rule": "reverses_recent_decision",
            "message": "blocked",
        },
    )
    assert result["resolution_tier"] == "haiku"
    assert result["verdict"] == "modify"


def test_resolve_guardrail_fleet_mock_uses_sonnet_tier(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    from helm import resolve_guardrail

    agents = {f"agent_{i}": {"intent": f"i{i}", "code": ""} for i in range(5)}
    result = resolve_guardrail(
        agents["agent_0"],
        agents["agent_1"],
        guardrail_context={
            "proposed_action": {"agent_id": "agent_4", "file_path": "x.py"},
            "rule": "file_overlap",
            "message": "blocked",
        },
        fleet_agents=agents,
    )
    assert result["resolution_tier"] == "sonnet"
