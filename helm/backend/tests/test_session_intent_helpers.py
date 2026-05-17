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


def test_file_clusters_groups_agents_by_path():
    store = SessionStore()
    sid = "s1"
    store.record_intent(session_id=sid, agent_id="a", file_path="app/auth/handlers.py", intent="auth")
    store.record_intent(session_id=sid, agent_id="b", file_path="app/auth/handlers.py", intent="auth b")
    store.record_intent(session_id=sid, agent_id="c", file_path="app/billing/invoices.py", intent="billing")

    clusters = store.file_clusters(sid, min_agents=2)
    assert clusters == {"app/auth/handlers.py": ["a", "b"]}


def test_file_clusters_ignores_single_agent_files():
    store = SessionStore()
    sid = "s2"
    store.record_intent(session_id=sid, agent_id="a", file_path="app/a.py", intent="a")
    store.record_intent(session_id=sid, agent_id="b", file_path="app/b.py", intent="b")
    assert store.file_clusters(sid, min_agents=2) == {}
