from store.sessions import SessionStore


def test_intents_on_file_returns_agent_and_intent():
    store = SessionStore()
    store.record_intent(session_id="s", agent_id="a1", file_path="f.py", intent="cache")
    store.record_intent(session_id="s", agent_id="a2", file_path="f.py", intent="auth")
    rows = store.intents_on_file("s", "f.py", exclude="a2")
    assert len(rows) == 1
    assert rows[0]["agent_id"] == "a1"
    assert rows[0]["intent"] == "cache"


def test_latest_intent_for_agent_returns_most_recent():
    store = SessionStore()
    store.record_intent(session_id="s", agent_id="a1", file_path="f.py", intent="old")
    store.record_intent(session_id="s", agent_id="a1", file_path="f.py", intent="new")
    assert store.latest_intent_for_agent("s", "a1", "f.py") == "new"
