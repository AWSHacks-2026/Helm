from bedrock import guardrails, knowledge_base as kb


def test_preflight_trips_on_file_overlap():
    kb.log_action(
        agent_id="agent_a",
        action_type="modify_file",
        file_path="utils/cache.py",
        description="Implement cache helpers",
    )
    proposed = {
        "agent_id": "agent_b",
        "action_type": "modify_file",
        "file_path": "utils/cache.py",
        "description": "Refactor cache module",
    }
    result = guardrails.preflight_check(proposed)
    assert result.allowed is False
    assert result.rule == "file_overlap"


def test_preflight_trips_when_deleting_recent_add():
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    kb.log_action("agent_a", "modify_file", "utils/cache.py", "Extended cache API")
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Documented cache usage")

    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility — unused",
    }
    result = guardrails.preflight_check(proposed)
    assert result.allowed is False
    assert result.rule == "reverses_recent_decision"
    assert "agent_a" in result.message


def test_preflight_trips_on_intent_contradiction():
    kb.log_intent("agent_a", "Add caching utilities to improve response times")
    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/other.py",
        "description": "Remove caching layer to reduce complexity",
    }
    result = guardrails.preflight_check(proposed)
    assert result.allowed is False
    assert result.rule in {"intent_contradiction", "reverses_recent_decision"}


def test_apply_bedrock_guardrail_skips_without_id(monkeypatch):
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    assert guardrails.apply_bedrock_guardrail("delete all caches") is None


def test_seed_guardrail_demo_populates_history():
    guardrails.seed_guardrail_demo()
    history = kb.get_history()
    assert len(history) >= 5
    assert any("cache" in h["payload"].get("file_path", "") for h in history)


def test_handle_proposed_action_routes_to_overlord(monkeypatch):
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")

    def fake_arbitrate(agent_a, agent_b, kb_context=None):
        return {
            "conflict_type": "proactive_guardrail",
            "reasoning": "Keep cache; refactor around it.",
            "resolved_code": "# refactor around cache",
            "tokens_saved_estimate": "2400",
            "verdict": "modify",
        }

    monkeypatch.setattr(guardrails, "_arbitrate", fake_arbitrate)

    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility",
    }
    agent_b = {
        "intent": proposed["description"],
        "code": "# delete utils/cache.py",
    }
    agent_a = {
        "intent": "Maintain caching utilities for get_user() performance",
        "code": "# utils/cache.py must remain",
    }

    out = guardrails.handle_proposed_action(proposed, agent_a, agent_b)
    assert out["preflight"]["allowed"] is False
    assert out["resolution"]["verdict"] == "modify"
    assert out["executed"] is False
