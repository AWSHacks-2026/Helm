from bedrock.guardrails import check_action
from store.sessions import SessionStore


def test_write_allowed_when_no_other_agents_on_file():
    store = SessionStore()
    result = check_action(
        session_id="s1",
        agent_id="a2",
        file_path="f.py",
        action="write",
        proposed_code="x",
        session_store=store,
    )
    assert result.allowed is True


def test_write_blocked_when_other_agent_has_intent_on_file():
    store = SessionStore()
    store.record_intent(
        session_id="s1",
        agent_id="a1",
        file_path="f.py",
        intent="caching",
    )
    result = check_action(
        session_id="s1",
        agent_id="a2",
        file_path="f.py",
        action="write",
        proposed_code="x",
        session_store=store,
    )
    assert result.allowed is False
    assert result.route_to_overlord is True
