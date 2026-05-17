import json

from bedrock import knowledge_base as kb


def test_log_action_and_get_history():
    kb.log_action(
        agent_id="agent_a",
        action_type="add_file",
        file_path="utils/cache.py",
        description="Added caching utility",
    )
    history = kb.get_history()
    assert len(history) == 1
    assert history[0]["record_type"] == "action"
    assert history[0]["agent_id"] == "agent_a"
    assert history[0]["payload"]["file_path"] == "utils/cache.py"


def test_log_intent_includes_text():
    kb.log_intent(agent_id="agent_b", intent="Minimize dependencies in utils/")
    history = kb.get_history(record_type="intent")
    assert history[0]["payload"]["intent"] == "Minimize dependencies in utils/"


def test_retrieve_context_local_keyword_match():
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    kb.log_intent("agent_b", "Remove unused utilities")
    results = kb.retrieve_context("caching utility agent_a", max_results=3)
    assert len(results) >= 1
    assert any("cache" in json.dumps(r).lower() for r in results)
