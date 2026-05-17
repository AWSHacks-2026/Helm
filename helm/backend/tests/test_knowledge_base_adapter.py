from bedrock import knowledge_base


def test_append_and_list_history(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_PATH", str(tmp_path / "session.json"))
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "true")
    knowledge_base.append_event(
        "sess_kb",
        {
            "event_type": "intent_declared",
            "payload": {"agent_id": "a1", "file_path": "f.py", "intent": "cache"},
        },
    )
    history = knowledge_base.list_history("sess_kb")
    assert len(history) >= 1
    assert any(h["event_type"] == "intent_declared" for h in history)
