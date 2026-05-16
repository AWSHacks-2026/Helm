from bedrock import guardrails, knowledge_base as kb


def test_kb_context_forwarded_to_arbitrate(monkeypatch):
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    captured: dict = {}

    def fake_arbitrate(agent_a, agent_b, kb_context=None):
        captured["kb_context"] = kb_context
        return {
            "reasoning": "ok",
            "conflict_type": "proactive_guardrail",
            "verdict": "modify",
        }

    monkeypatch.setattr(guardrails, "_arbitrate", fake_arbitrate)

    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility",
    }
    guardrails.handle_proposed_action(
        proposed,
        {"intent": "keep cache", "code": "# keep"},
        {"intent": "remove cache", "code": "# delete"},
    )
    assert captured["kb_context"] is not None
    assert len(captured["kb_context"]) > 0
